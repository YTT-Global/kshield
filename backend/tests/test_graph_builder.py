"""Regression tests for the repo-wide graph builder (M1).

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_graph_builder.py -v
"""
from app.engine.graph_builder import build_repo_graph


def _graph(files):
    return build_repo_graph(files)


class TestRouteDetection:
    # ── TRUE POSITIVES ──────────────────────────────────────────────────────

    def test_get_route_detected(self):
        code = """
from fastapi import APIRouter
router = APIRouter()

@router.get("/items")
async def list_items():
    return []
"""
        g = _graph([("routes.py", code)])
        assert len(g.routes) == 1
        assert g.routes[0].method == "GET"
        assert g.routes[0].path == "/items"
        assert g.routes[0].handler == "list_items"

    def test_multiple_route_methods_detected(self):
        code = """
from fastapi import APIRouter
router = APIRouter()

@router.post("/a")
async def a(): pass

@router.delete("/b/{id}")
async def b(id: str): pass

@router.get("/c")
def c(): pass
"""
        g = _graph([("routes.py", code)])
        methods = {r.method for r in g.routes}
        assert methods == {"POST", "DELETE", "GET"}

    def test_sync_and_async_both_detected(self):
        code = """
@app.get("/sync")
def sync_route(): pass

@app.get("/async")
async def async_route(): pass
"""
        g = _graph([("main.py", code)])
        assert len(g.routes) == 2

    # ── FALSE POSITIVE SUPPRESSION ──────────────────────────────────────────

    def test_route_decorator_inside_docstring_not_detected(self):
        # This is the exact case that beats naive grep: a route-shaped string
        # sitting inside a docstring is not a real decorator node.
        code = '''
def helper():
    """Example usage: @app.get('/fake') to define a route."""
    pass
'''
        g = _graph([("helper.py", code)])
        assert g.routes == []

    def test_non_route_decorator_ignored(self):
        code = """
class Foo:
    @staticmethod
    def bar():
        pass

    @property
    def baz(self):
        return 1
"""
        g = _graph([("foo.py", code)])
        assert g.routes == []

    def test_plain_function_no_route(self):
        code = "def helper(x):\n    return x + 1\n"
        g = _graph([("utils.py", code)])
        assert g.routes == []


class TestGuardNameExtraction:
    def test_signature_depends_captured(self):
        code = """
from fastapi import Depends
@app.get("/profile")
async def profile(user=Depends(get_current_user)):
    return user
"""
        g = _graph([("routes.py", code)])
        assert g.routes[0].guard_names == ["get_current_user"]

    def test_decorator_dependencies_captured(self):
        code = """
from fastapi import Depends
@app.get("/admin", dependencies=[Depends(require_admin)])
async def admin_panel():
    return {}
"""
        g = _graph([("routes.py", code)])
        assert g.routes[0].guard_names == ["require_admin"]

    def test_unrelated_dependency_still_captured_by_name(self):
        # graph_builder just records the name — judging whether it's an auth
        # guard is access_control.py's job, not this one's.
        code = """
from fastapi import Depends
@router.post("/scan")
async def scan(db=Depends(get_db_session)):
    pass
"""
        g = _graph([("scan.py", code)])
        assert g.routes[0].guard_names == ["get_db_session"]

    def test_no_dependency_gives_empty_guard_names(self):
        code = """
@app.get("/open")
async def open_route():
    pass
"""
        g = _graph([("routes.py", code)])
        assert g.routes[0].guard_names == []


class TestImportsAndSymbols:
    def test_python_imports_reduced_to_top_level(self):
        code = "import numpy.random\nfrom os import path\nimport requests\n"
        g = _graph([("app.py", code)])
        assert set(g.imports["app.py"]) == {"numpy", "os", "requests"}

    def test_function_and_class_names_captured_as_symbols(self):
        code = """
class Foo:
    pass

def bar():
    pass

async def baz():
    pass
"""
        g = _graph([("app.py", code)])
        assert set(g.symbols["app.py"]) == {"Foo", "bar", "baz"}

    def test_js_subpath_import_reduced_to_package_root(self):
        code = 'import { render } from "react-dom/client";\n'
        g = _graph([("main.tsx", code)])
        assert g.imports["main.tsx"] == ["react-dom"]

    def test_js_scoped_package_keeps_two_segments(self):
        code = 'import x from "@vitejs/plugin-react/utils";\n'
        g = _graph([("vite.config.ts", code)])
        assert g.imports["vite.config.ts"] == ["@vitejs/plugin-react"]

    def test_js_relative_import_untouched_by_root_reduction(self):
        code = 'import { x } from "../api/client";\n'
        g = _graph([("component.tsx", code)])
        # still starts with "." so downstream relative-import filters still work
        assert g.imports["component.tsx"][0].startswith(".")

    def test_non_code_file_gets_empty_imports_and_symbols(self):
        g = _graph([("README.md", "# Hello\nSome text.\n")])
        assert g.imports["README.md"] == []
        assert g.symbols["README.md"] == []


class TestParseErrorIsolation:
    def test_broken_file_recorded_without_crashing_batch(self):
        files = [
            ("broken.py", "def oops(:\n"),
            ("fine.py", "def ok():\n    return 1\n"),
        ]
        g = _graph(files)
        assert "broken.py" in g.parse_errors
        assert "fine.py" not in g.parse_errors
        assert g.symbols["fine.py"] == ["ok"]

    def test_broken_file_contributes_no_routes(self):
        g = _graph([("broken.py", "@app.get('/x'\ndef f(:\n")])
        assert g.routes == []
