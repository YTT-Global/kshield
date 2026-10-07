"""Regression tests for the local (no-network) dependency hygiene checks (M5).

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_dependency_audit.py -v
"""
from app.engine.dependency_audit import parse_declared_dependencies, check_dependency_hygiene, workspace_package_names


def _hygiene(imports_by_file, manifest_files=()):
    declared = parse_declared_dependencies(list(manifest_files))
    return check_dependency_hygiene(imports_by_file, declared)


class TestTyposquatDetection:
    # ── TRUE POSITIVES ──────────────────────────────────────────────────────

    def test_close_typo_of_popular_package_flagged(self):
        r = _hygiene({"app.py": ["reqeusts"]})
        assert len(r) == 1
        assert r[0]["anomaly_type"] == "Possible Typosquat"
        assert "requests" in r[0]["description"]

    def test_edit_distance_one_is_critical(self):
        # "numpy" -> "numpu" is a single substitution
        r = _hygiene({"app.py": ["numpu"]})
        assert r[0]["severity"] == "CRITICAL"

    def test_edit_distance_two_is_high(self):
        r = _hygiene({"app.py": ["reqeusts"]})  # distance 2 from "requests"
        assert r[0]["severity"] == "HIGH"

    def test_npm_typo_flagged(self):
        r = _hygiene({"app.tsx": ["axois"]})  # distance 2 from "axios"
        assert any(f["anomaly_type"] == "Possible Typosquat" for f in r)

    # ── FALSE POSITIVE SUPPRESSION ──────────────────────────────────────────

    def test_declared_import_not_flagged_even_if_undeclared_would_typo_match(self):
        manifest = [("requirements.txt", "reqeusts==1.0\n")]
        r = _hygiene({"app.py": ["reqeusts"]}, manifest)
        assert r == []

    def test_popular_package_exact_match_not_flagged(self):
        r = _hygiene({"app.py": ["requests", "numpy", "fastapi"]})
        assert r == []

    def test_unrelated_import_too_far_from_any_popular_name(self):
        r = _hygiene({"app.py": ["my_totally_custom_thing"]})
        assert not any(f["anomaly_type"] == "Possible Typosquat" for f in r)

    def test_registry_verified_real_package_not_flagged_as_typosquat(self):
        # Real bug found in the adk-python pilot: "retry" (a real PyPI
        # package) is edit-distance 2 from "poetry", and "mcp" (a real
        # package) is edit-distance 2 from "mypy". If the registry already
        # confirmed the package independently exists, it isn't squatting.
        from app.engine.dependency_audit import check_dependency_hygiene, parse_declared_dependencies
        declared = parse_declared_dependencies([])
        r = check_dependency_hygiene({"app.py": ["retry"]}, declared, registry_verified={"retry": True})
        assert not any(f["anomaly_type"] == "Possible Typosquat" for f in r)
        # Still undeclared, just not a typosquat — that signal shouldn't vanish.
        assert any(f["anomaly_type"] == "Undeclared Dependency" for f in r)

    def test_registry_unverified_still_flags_typosquat(self):
        # Confirms the fix is additive, not a blanket suppression — a package
        # that genuinely doesn't resolve on the registry is still flagged.
        from app.engine.dependency_audit import check_dependency_hygiene, parse_declared_dependencies
        declared = parse_declared_dependencies([])
        r = check_dependency_hygiene({"app.py": ["reqeusts"]}, declared, registry_verified={"reqeusts": False})
        assert any(f["anomaly_type"] == "Possible Typosquat" for f in r)


class TestUndeclaredDependency:
    def test_undeclared_non_typo_import_flagged_low(self):
        r = _hygiene({"app.py": ["some_internal_looking_but_unknown_pkg"]})
        assert len(r) == 1
        assert r[0]["anomaly_type"] == "Undeclared Dependency"
        assert r[0]["severity"] == "LOW"

    def test_declared_import_not_flagged(self):
        manifest = [("requirements.txt", "flask>=2.0\n")]
        r = _hygiene({"app.py": ["flask"]}, manifest)
        assert r == []


class TestStdlibAndBuiltinExclusion:
    def test_python_stdlib_not_flagged(self):
        r = _hygiene({"app.py": ["os", "sys", "re", "json", "pathlib", "typing"]})
        assert r == []

    def test_node_builtins_not_flagged(self):
        r = _hygiene({"app.ts": ["fs", "path", "child_process", "https"]})
        assert r == []

    def test_node_protocol_prefixed_builtins_not_flagged(self):
        # Real false positive found in the ytt-payments pilot — modern Node
        # code increasingly uses "node:crypto" instead of bare "crypto".
        r = _hygiene({"app.ts": ["node:path", "node:url", "node:crypto"]})
        assert r == []

    def test_ambient_module_not_flagged(self):
        r = _hygiene({"extension.ts": ["vscode"]})
        assert r == []


class TestRelativeAndFirstPartyExclusion:
    def test_relative_import_not_flagged(self):
        r = _hygiene({"src/App.tsx": ["./components/Dashboard", "../api/client"]})
        assert r == []

    def test_ts_path_alias_not_flagged(self):
        # Real bug found in the synapse-console pilot: "@/hooks" is a Vite/
        # Next.js path alias, not a scoped npm package — a real scoped
        # package always has a non-empty scope, e.g. "@fastify/cors".
        r = _hygiene({"src/App.tsx": ["@/hooks", "@/lib", "@/components"]})
        assert r == []

    def test_real_scoped_package_still_checked(self):
        # Distinguishes the fix above from a real scoped package with the
        # same "starts with @" shape.
        r = _hygiene({"src/App.tsx": ["@totally-unknown-scope/made-up-pkg"]})
        assert any(f["anomaly_type"] == "Undeclared Dependency" for f in r)

    def test_first_party_directory_name_not_flagged(self):
        # "app" is a directory that exists in this very batch, so importing
        # something named "app" is this codebase, not a missing dependency.
        r = _hygiene({
            "app/main.py": ["app"],
            "app/models/user.py": [],
        })
        assert r == []

    def test_first_party_file_stem_not_flagged(self):
        r = _hygiene({
            "app/utils.py": ["utils"],
        })
        assert r == []


class TestManifestParsing:
    def test_requirements_txt_strips_version_specifiers(self):
        content = "fastapi>=0.111\nuvicorn[standard]>=0.29\nnumpy==1.26.0\n# a comment\n"
        declared = parse_declared_dependencies([("requirements.txt", content)])
        assert "fastapi" in declared
        assert "uvicorn" in declared
        assert "numpy" in declared

    def test_package_json_parses_both_dependency_sections(self):
        content = '{"dependencies": {"react": "^18.0"}, "devDependencies": {"vite": "^5.0"}}'
        declared = parse_declared_dependencies([("package.json", content)])
        assert "react" in declared
        assert "vite" in declared

    def test_malformed_package_json_does_not_crash(self):
        declared = parse_declared_dependencies([("package.json", "{not valid json")])
        assert declared == set()

    def test_subpath_import_matches_declared_package_root(self):
        # react-dom is declared; react-dom/client is what's actually imported.
        # graph_builder already reduces this to "react-dom" before it gets here.
        manifest = [("package.json", '{"dependencies": {"react-dom": "^18.0"}}')]
        r = _hygiene({"main.tsx": ["react-dom"]}, manifest)
        assert r == []


class TestPyprojectTomlParsing:
    # Real bug found in the adk-python pilot: pyproject.toml parsing was
    # previously skipped entirely, so a repo with no requirements.txt (using
    # only pyproject.toml, the modern standard) had every single import read
    # as undeclared — 255 false positives in one repo.

    def test_pep621_dependencies_array_parsed(self):
        content = '[project]\nname = "demo"\ndependencies = ["requests>=2.0", "click"]\n'
        declared = parse_declared_dependencies([("pyproject.toml", content)])
        assert "requests" in declared
        assert "click" in declared

    def test_pep621_optional_dependencies_parsed(self):
        content = (
            '[project]\nname = "demo"\ndependencies = []\n'
            '[project.optional-dependencies]\ndev = ["pytest>=7.0", "black"]\n'
        )
        declared = parse_declared_dependencies([("pyproject.toml", content)])
        assert "pytest" in declared
        assert "black" in declared

    def test_poetry_dependencies_table_parsed(self):
        content = (
            '[tool.poetry.dependencies]\npython = "^3.11"\nfastapi = "^0.111"\nuvicorn = {extras = ["standard"], version = "^0.29"}\n'
        )
        declared = parse_declared_dependencies([("pyproject.toml", content)])
        assert "fastapi" in declared
        assert "uvicorn" in declared
        assert "python" not in declared

    def test_poetry_group_dependencies_parsed(self):
        content = (
            '[tool.poetry.group.dev.dependencies]\npytest = "^7.0"\n'
        )
        declared = parse_declared_dependencies([("pyproject.toml", content)])
        assert "pytest" in declared

    def test_pyproject_declared_import_not_flagged_end_to_end(self):
        manifest = [("pyproject.toml", '[project]\nname = "demo"\ndependencies = ["fastapi>=0.111"]\n')]
        r = _hygiene({"app.py": ["fastapi"]}, manifest)
        assert r == []

    def test_malformed_pyproject_toml_does_not_crash(self):
        declared = parse_declared_dependencies([("pyproject.toml", "not [ valid toml =")])
        assert declared == set()


class TestWorkspacePackageNames:
    # Real bug found in the webstudio pilot: a monorepo workspace package
    # (declared via its own package.json's "name" field) gets imported with
    # a scoped-npm-looking specifier — indistinguishable from a real external
    # package by name shape alone.
    def test_own_package_json_name_extracted(self):
        content = '{"name": "@webstudio-is/template", "version": "1.0.0"}'
        names = workspace_package_names([("packages/template/package.json", content)])
        assert "@webstudio-is/template" in names

    def test_missing_name_field_ignored(self):
        content = '{"version": "1.0.0"}'
        names = workspace_package_names([("package.json", content)])
        assert names == set()

    def test_malformed_json_does_not_crash(self):
        names = workspace_package_names([("package.json", "{not valid")])
        assert names == set()

    def test_non_package_json_files_ignored(self):
        names = workspace_package_names([("app.py", '{"name": "not-relevant"}')])
        assert names == set()
