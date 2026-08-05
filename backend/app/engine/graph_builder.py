import ast
import re
from dataclasses import dataclass, field


@dataclass
class RouteInfo:
    path: str
    method: str
    handler: str
    filename: str
    line: int
    decorators: list[str] = field(default_factory=list)
    guard_names: list[str] = field(default_factory=list)


@dataclass
class RepoGraph:
    files: list[str] = field(default_factory=list)
    imports: dict[str, list[str]] = field(default_factory=dict)
    symbols: dict[str, list[str]] = field(default_factory=dict)
    routes: list[RouteInfo] = field(default_factory=list)
    parse_errors: dict[str, str] = field(default_factory=dict)


_ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}
_JS_IMPORT_RE = re.compile(r"""(?:import\s+.*?from\s+|require\()\s*['"]([^'"]+)['"]""")


def _decorator_method(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        return _decorator_method(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _decorator_qualname(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        return _decorator_qualname(node.func)
    if isinstance(node, ast.Attribute):
        base = _decorator_qualname(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _route_path(node: ast.expr) -> str:
    if isinstance(node, ast.Call) and node.args:
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    return ""


def _guard_target_name(call: ast.Call) -> str:
    """The callable passed to Depends(...) / Security(...), e.g. "get_current_user"."""
    if call.args:
        arg = call.args[0]
        if isinstance(arg, ast.Name):
            return arg.id
        if isinstance(arg, ast.Attribute):
            return arg.attr
    return ""


def _guard_names_from_call_list(value: ast.expr) -> list[str]:
    names = []
    if isinstance(value, ast.List):
        for elt in value.elts:
            if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name) and elt.func.id in ("Depends", "Security"):
                names.append(_guard_target_name(elt))
    return names


def _guard_names_from_decorator(dec: ast.expr) -> list[str]:
    """Dependencies declared on the route itself: @app.get(..., dependencies=[Depends(x)])."""
    if not isinstance(dec, ast.Call):
        return []
    for kw in dec.keywords:
        if kw.arg == "dependencies":
            return _guard_names_from_call_list(kw.value)
    return []


def _guard_names_from_signature(args: ast.arguments) -> list[str]:
    """Dependencies injected via the handler's own parameters, e.g. user: User = Depends(get_current_user)."""
    names = []
    all_defaults = [*args.defaults, *(d for d in args.kw_defaults if d is not None)]
    for d in all_defaults:
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id in ("Depends", "Security"):
            names.append(_guard_target_name(d))
    return names


# Real bug found in the retail-quick-commerce pilot: a Razorpay webhook route
# calls verify_webhook_signature(body, signature) in its own body — a real,
# working guard — but reads as completely unguarded, identical to one that
# does nothing, because Depends()/Security() is the only guard shape the
# checks above can see. A webhook is called by a third party's servers, not
# a logged-in user, so it can never carry a Depends(get_current_user)
# regardless of how well it's actually protected.
_BODY_GUARD_KEYWORDS = ("signature", "hmac")


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _body_guard_names(body: list[ast.stmt]) -> list[str]:
    names = []
    for stmt in body:
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Call):
                name = _call_name(sub)
                if name and any(keyword in name.lower() for keyword in _BODY_GUARD_KEYWORDS):
                    names.append(name)
    return names


def _extract_python(filename: str, content: str, graph: RepoGraph) -> None:
    try:
        tree = ast.parse(content, filename=filename)
    except SyntaxError as e:
        graph.parse_errors[filename] = str(e)
        graph.imports[filename] = []
        graph.symbols[filename] = []
        return

    imports: list[str] = []
    symbols: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(node.name)
            for dec in node.decorator_list:
                if _decorator_method(dec) in _ROUTE_METHODS:
                    guard_names = (
                        _guard_names_from_decorator(dec)
                        + _guard_names_from_signature(node.args)
                        + _body_guard_names(node.body)
                    )
                    graph.routes.append(RouteInfo(
                        path=_route_path(dec),
                        method=_decorator_method(dec).upper(),
                        handler=node.name,
                        filename=filename,
                        line=node.lineno,
                        decorators=[_decorator_qualname(d) for d in node.decorator_list],
                        guard_names=guard_names,
                    ))
        elif isinstance(node, ast.ClassDef):
            symbols.append(node.name)

    graph.imports[filename] = sorted(set(imports))
    graph.symbols[filename] = symbols


def _js_package_root(raw_import: str) -> str:
    """Reduce a subpath import like "react-dom/client" to its package root
    "react-dom" — matches sandbox.py's own resolution for npm hallucination
    checks, so every consumer of graph.imports sees the same package names."""
    if raw_import.startswith("@"):
        return "/".join(raw_import.split("/")[:2])
    return raw_import.split("/")[0]


def _extract_generic(filename: str, content: str, graph: RepoGraph) -> None:
    roots = {_js_package_root(raw) for raw in _JS_IMPORT_RE.findall(content)}
    graph.imports[filename] = sorted(roots)
    graph.symbols[filename] = []


def build_repo_graph(files: list[tuple[str, str]]) -> RepoGraph:
    graph = RepoGraph(files=[filename for filename, _ in files])

    for filename, content in files:
        if filename.endswith(".py"):
            _extract_python(filename, content, graph)
        elif filename.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
            _extract_generic(filename, content, graph)
        else:
            graph.imports[filename] = []
            graph.symbols[filename] = []

    return graph
