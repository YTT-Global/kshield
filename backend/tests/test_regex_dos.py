"""Regression tests for polynomial-ReDoS in the JS/TS extraction regexes.

kshield scans untrusted code (org-audit.sh clones other people's repos), so a
crafted file must not be able to stall the backend. CodeQL flagged both of
these as py/polynomial-redos; the inputs below are the shapes it reported.

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_regex_dos.py -v
"""
import time

import pytest

from app.engine.graph_builder import _JS_IMPORT_RE, _js_package_root
from app.engine.sandbox import _strip_js_comments

N = 20_000
# The old regexes took 5-40s on these sizes; the fixed code takes milliseconds.
# The budget is deliberately loose so a slow CI runner can't make it flaky.
BUDGET_SECONDS = 2.0


def _elapsed(fn, arg) -> float:
    start = time.perf_counter()
    fn(arg)
    return time.perf_counter() - start


# ─────────────────────── _strip_js_comments: speed ──────────────────────────

@pytest.mark.parametrize("payload", [
    "/*" + "a/*" * N,            # unterminated block comments
    '"' + '\\"' * N,             # unterminated double-quoted string
    "'" + "\\'" * N,             # unterminated single-quoted string
    "`" + "\\`" * N,             # unterminated template string
    "/*" * N,
    '"' * N,
], ids=["block", "double", "single", "template", "block-bare", "quote-bare"])
def test_strip_js_comments_is_linear_on_hostile_input(payload):
    assert _elapsed(_strip_js_comments, payload) < BUDGET_SECONDS


# ─────────────────────── _strip_js_comments: behavior ───────────────────────

class TestStripJsComments:
    def test_line_comment_removed(self):
        assert "from 'x'" not in _strip_js_comments("// the type from 'x'\nconst a = 1;")

    def test_block_comment_removed_across_lines(self):
        out = _strip_js_comments("a /* one\ntwo from 'x' */ b")
        assert "from" not in out and out.startswith("a ") and out.endswith(" b")

    def test_comment_marker_inside_string_is_preserved(self):
        code = 'const u = "https://example.com/a"; // trailing'
        out = _strip_js_comments(code)
        assert '"https://example.com/a"' in out and "trailing" not in out

    def test_escaped_quote_does_not_end_string(self):
        code = r'const s = "a \" // not a comment"; x'
        assert "// not a comment" in _strip_js_comments(code)

    def test_unterminated_block_comment_left_alone(self):
        assert _strip_js_comments("a /* never closed") == "a /* never closed"

    def test_unterminated_string_left_alone(self):
        assert _strip_js_comments('a "never closed') == 'a "never closed'

    def test_a_dead_quote_does_not_hide_later_valid_strings(self):
        # The lone apostrophe never terminates, but the double-quoted string
        # after it is still a real string and must survive intact.
        out = _strip_js_comments("don't \"keep // this\" x")
        assert '"keep // this"' in out

    def test_empty_and_plain_code_unchanged(self):
        assert _strip_js_comments("") == ""
        assert _strip_js_comments("const a = b / c;") == "const a = b / c;"


# ───────────────────────── _JS_IMPORT_RE: speed ─────────────────────────────

@pytest.mark.parametrize("payload", [
    "import " + " " * (N * 5),
    "require(" + " " * (N * 5),
    "import x " * (N // 2),
], ids=["import-spaces", "require-spaces", "many-imports-one-line"])
def test_js_import_regex_is_bounded_on_hostile_input(payload):
    assert _elapsed(_JS_IMPORT_RE.findall, payload) < BUDGET_SECONDS


# ───────────────────────── _JS_IMPORT_RE: behavior ──────────────────────────

class TestJsImportRegex:
    @pytest.mark.parametrize("code, expected", [
        ("import React from 'react';", ["react"]),
        ('import { a, b } from "@scope/pkg/sub";', ["@scope/pkg/sub"]),
        ("import * as x from 'lodash/fp'", ["lodash/fp"]),
        ("import type { T } from 'zod'", ["zod"]),
        ("const x = require('left-pad')", ["left-pad"]),
        ("const x = require(  'left-pad'  )", ["left-pad"]),
        ("import a from 'one'; import b from 'two'", ["one", "two"]),
    ])
    def test_extracts_package(self, code, expected):
        assert _JS_IMPORT_RE.findall(code) == expected

    def test_does_not_match_prose_without_an_import_keyword(self):
        assert _JS_IMPORT_RE.findall("the type from 'proxy.settings.get'") == []

    def test_does_not_span_lines(self):
        assert _JS_IMPORT_RE.findall("import {\n  a,\n} from 'x'") == []

    def test_package_root_reduction_still_applies(self):
        roots = {_js_package_root(r) for r in _JS_IMPORT_RE.findall(
            "import c from 'react-dom/client'; import s from '@a/b/c'")}
        assert roots == {"react-dom", "@a/b"}
