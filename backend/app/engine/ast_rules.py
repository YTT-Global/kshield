import ast

# Paths that are intentionally public — skip authentication check
_PUBLIC_PATHS: frozenset = frozenset([
    "/", "/health", "/healthz", "/health-check", "/healthcheck",
    "/ping", "/pong", "/ready", "/readiness", "/liveness", "/alive",
    "/docs", "/redoc", "/openapi.json", "/openapi.yaml",
    "/metrics", "/status", "/version", "/info",
    "/favicon.ico", "/robots.txt", "/sitemap.xml",
])

# HTTP methods that mutate state — unauthenticated access is a harder violation
_MUTATION_METHODS: frozenset = frozenset(["post", "put", "delete", "patch"])


def _route_path(decorator: ast.expr) -> str | None:
    """Extract the path string from @app.get('/path') or @router.post('/path')."""
    if isinstance(decorator, ast.Call) and decorator.args:
        first = decorator.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    return None


def _decorator_has_dependencies(decorator: ast.expr) -> bool:
    """Return True for @app.get('/path', dependencies=[Depends(...)]) style guards."""
    if not isinstance(decorator, ast.Call):
        return False
    return any(kw.arg == "dependencies" for kw in decorator.keywords)


def _decorator_method(decorator: ast.expr) -> str | None:
    """Return the HTTP method name ('get', 'post', etc.) from a route decorator."""
    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
        return decorator.func.attr
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    return None


class StructuralSecurityAuditor(ast.NodeVisitor):
    def __init__(self):
        self.violations = []

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        http_method: str | None = None
        route_path: str | None = None
        is_api_endpoint = False

        for dec in node.decorator_list:
            method = _decorator_method(dec)
            if method in ("get", "post", "put", "delete", "patch", "route"):
                is_api_endpoint = True
                http_method = method
                route_path = _route_path(dec)

                # Guard via decorator's dependencies=[Depends(...)] kwarg
                if _decorator_has_dependencies(dec):
                    self.generic_visit(node)
                    return

        if not is_api_endpoint:
            self.generic_visit(node)
            return

        # Skip known public / health / docs paths — intentionally unauthenticated
        if route_path and route_path in _PUBLIC_PATHS:
            self.generic_visit(node)
            return

        # Check function signature for Depends() / Security() guards
        all_defaults = [
            *node.args.defaults,
            *(d for d in node.args.kw_defaults if d is not None),
        ]
        has_auth = any(
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Name)
            and d.func.id in ("Depends", "Security")
            for d in all_defaults
        )

        if not has_auth:
            is_mutation = http_method in _MUTATION_METHODS
            severity = "HIGH" if is_mutation else "MEDIUM"
            path_hint = f" '{route_path}'" if route_path else ""
            method_hint = f"@{http_method}" if http_method else "route"

            self.violations.append({
                "line_number": node.lineno,
                "anomaly_type": "Broken Access Control",
                "severity": severity,
                "description": (
                    f"{method_hint} endpoint{path_hint} '{node.name}' has no authentication guard. "
                    f"Add Depends(get_current_user) to the function signature "
                    f"or dependencies=[Depends(...)] to the decorator."
                ),
                "code_snippet": f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}(...):",
            })

        self.generic_visit(node)

    # Covers  def route():  — sync handlers
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)

    # Covers  async def route():  — FastAPI routes are almost always async
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)


def run_ast_structural_scan(code_data: str, filename: str) -> list:
    if not filename.endswith(".py"):
        return []
    try:
        tree = ast.parse(code_data)
        auditor = StructuralSecurityAuditor()
        auditor.visit(tree)
        return auditor.violations
    except SyntaxError as err:
        return [{
            "line_number": err.lineno or 1,
            "anomaly_type": "Syntax Violation",
            "severity": "MEDIUM",
            "description": f"Python syntax error: {err.msg}. This often indicates truncated AI-generated code.",
            "code_snippet": err.text.strip() if err.text else "",
        }]
