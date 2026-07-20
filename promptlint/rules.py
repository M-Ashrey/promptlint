"""Lint rules for prompt/agent-instruction files.

Each rule is a small function taking a :class:`LintContext` and yielding
:class:`Finding` objects. Rules are intentionally independent so users can
select or ignore them individually.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator, List

from .tokens import count_tokens

SEVERITIES = ("error", "warning", "info")


@dataclass
class Finding:
    """A single lint result."""

    rule: str
    severity: str
    message: str
    line: int = 0

    def as_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
        }


@dataclass
class LintContext:
    """Everything a rule needs to inspect one file."""

    path: str
    text: str
    token_budget: int = 0
    model: str = "cl100k_base"
    lines: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.lines:
            self.lines = self.text.splitlines()


# --- individual rules -------------------------------------------------------

# Words/phrases that weaken an instruction. Kept small and opinionated.
_HEDGES = (
    "maybe",
    "perhaps",
    "possibly",
    "try to",
    "if possible",
    "i think",
    "sort of",
    "kind of",
    "you might want to",
    "it would be nice",
)

_PLACEHOLDER_RE = re.compile(
    r"(TODO|FIXME|XXX|TBD|\{\{[^}]*\}\}|<[A-Z_]{3,}>|\[INSERT[^\]]*\]|lorem ipsum)",
    re.IGNORECASE,
)


def rule_token_budget(ctx: LintContext) -> Iterator[Finding]:
    """Flag files that exceed the configured token budget."""
    if ctx.token_budget <= 0:
        return
    used = count_tokens(ctx.text, ctx.model)
    if used > ctx.token_budget:
        pct = round(used / ctx.token_budget * 100)
        yield Finding(
            rule="token-budget",
            severity="error",
            message=(
                f"file uses ~{used} tokens, {pct}% of the "
                f"{ctx.token_budget}-token budget"
            ),
            line=1,
        )


def rule_hedging(ctx: LintContext) -> Iterator[Finding]:
    """Flag hedging language that softens directives."""
    for i, line in enumerate(ctx.lines, start=1):
        low = line.lower()
        for hedge in _HEDGES:
            idx = low.find(hedge)
            if idx != -1:
                # avoid matching inside a longer word for single tokens
                yield Finding(
                    rule="hedging",
                    severity="warning",
                    message=f"hedging phrase {hedge!r} weakens the instruction",
                    line=i,
                )
                break


def rule_placeholders(ctx: LintContext) -> Iterator[Finding]:
    """Flag unresolved placeholders and TODO markers."""
    for i, line in enumerate(ctx.lines, start=1):
        m = _PLACEHOLDER_RE.search(line)
        if m:
            yield Finding(
                rule="placeholder",
                severity="error",
                message=f"unresolved placeholder {m.group(0)!r}",
                line=i,
            )


def rule_trailing_whitespace(ctx: LintContext) -> Iterator[Finding]:
    """Flag trailing whitespace, which bloats token counts silently."""
    for i, line in enumerate(ctx.lines, start=1):
        if line != line.rstrip():
            yield Finding(
                rule="trailing-whitespace",
                severity="info",
                message="trailing whitespace",
                line=i,
            )


def rule_heading_structure(ctx: LintContext) -> Iterator[Finding]:
    """Warn when heading levels jump (e.g. h1 -> h3), which hurts parsing."""
    prev = 0
    for i, line in enumerate(ctx.lines, start=1):
        m = re.match(r"^(#{1,6})\s+\S", line)
        if not m:
            continue
        level = len(m.group(1))
        if prev and level > prev + 1:
            yield Finding(
                rule="heading-jump",
                severity="warning",
                message=f"heading jumps from h{prev} to h{level}",
                line=i,
            )
        prev = level


def rule_long_lines(ctx: LintContext) -> Iterator[Finding]:
    """Flag very long unbroken lines that are hard to review in diffs."""
    limit = 400
    for i, line in enumerate(ctx.lines, start=1):
        if len(line) > limit:
            yield Finding(
                rule="long-line",
                severity="info",
                message=f"line is {len(line)} chars (>{limit})",
                line=i,
            )


def rule_empty_file(ctx: LintContext) -> Iterator[Finding]:
    """Flag empty or whitespace-only files."""
    if not ctx.text.strip():
        yield Finding(
            rule="empty-file",
            severity="error",
            message="file is empty",
            line=1,
        )


ALL_RULES: dict[str, Callable[[LintContext], Iterable[Finding]]] = {
    "token-budget": rule_token_budget,
    "hedging": rule_hedging,
    "placeholder": rule_placeholders,
    "trailing-whitespace": rule_trailing_whitespace,
    "heading-jump": rule_heading_structure,
    "long-line": rule_long_lines,
    "empty-file": rule_empty_file,
}


def run_rules(
    ctx: LintContext,
    select: Iterable[str] | None = None,
    ignore: Iterable[str] | None = None,
) -> List[Finding]:
    """Run rules against ``ctx`` and return sorted findings.

    ``select`` limits execution to the named rules; ``ignore`` removes named
    rules. ``select`` takes precedence when both are given.
    """
    names = list(ALL_RULES)
    if select:
        sel = set(select)
        names = [n for n in names if n in sel]
    if ignore:
        ign = set(ignore)
        names = [n for n in names if n not in ign]

    findings: List[Finding] = []
    for name in names:
        findings.extend(ALL_RULES[name](ctx))
    findings.sort(key=lambda f: (f.line, f.rule))
    return findings
