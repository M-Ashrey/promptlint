"""Unit tests for promptlint rules and token counting."""
from __future__ import annotations

import json
import subprocess
import sys

from promptlint.rules import LintContext, run_rules
from promptlint.tokens import count_tokens, _heuristic_tokens


def _rules_for(text: str, **kw):
    ctx = LintContext(path="x.md", text=text, **kw)
    return {f.rule for f in run_rules(ctx)}


def test_placeholder_detected():
    assert "placeholder" in _rules_for("Do the thing.\nTODO: finish this")


def test_placeholder_angle_and_braces():
    assert "placeholder" in _rules_for("Name is <PLACEHOLDER> here")
    assert "placeholder" in _rules_for("Value is {{var}} here")


def test_hedging_detected():
    assert "hedging" in _rules_for("Maybe you should try to help.")


def test_clean_text_has_no_findings():
    findings = _rules_for("# Title\n\nAlways respond in JSON.\n")
    assert findings == set()


def test_token_budget_triggers():
    text = "word " * 50
    findings = _rules_for(text, token_budget=5)
    assert "token-budget" in findings


def test_token_budget_off_by_default():
    text = "word " * 50
    assert "token-budget" not in _rules_for(text)


def test_heading_jump():
    assert "heading-jump" in _rules_for("# A\n\n### C too deep")


def test_trailing_whitespace():
    assert "trailing-whitespace" in _rules_for("line with space   \n")


def test_empty_file():
    assert "empty-file" in _rules_for("   \n  ")


def test_select_and_ignore():
    text = "Maybe try to do TODO   "
    ctx = LintContext(path="x.md", text=text)
    only = {f.rule for f in run_rules(ctx, select=["hedging"])}
    assert only == {"hedging"}
    without = {f.rule for f in run_rules(ctx, ignore=["hedging"])}
    assert "hedging" not in without


def test_heuristic_tokens_positive():
    assert _heuristic_tokens("hello world") >= 2
    assert count_tokens("") == 0


def test_cli_json_runs(tmp_path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("Maybe try to help.\nTODO fix\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "promptlint", str(f), "--format", "json", "--no-color"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1  # error-level placeholder present
    data = json.loads(proc.stdout)
    assert data["files"][0]["path"].endswith("CLAUDE.md")
    rules = {x["rule"] for x in data["files"][0]["findings"]}
    assert "placeholder" in rules and "hedging" in rules
