"""promptlint: a linter for prompt and agent-instruction files.

Checks Markdown-based prompt files (system prompts, CLAUDE.md, AGENTS.md,
*.prompt) for token-budget overruns, hedging language, leftover placeholders,
and structural issues that erode instruction quality.
"""
from __future__ import annotations

__version__ = "0.1.0"

from .rules import Finding, LintContext, run_rules  # noqa: E402,F401
from .tokens import count_tokens  # noqa: E402,F401
