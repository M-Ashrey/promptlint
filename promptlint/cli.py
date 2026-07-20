"""Command-line interface for promptlint."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from typing import List, Sequence

from . import __version__
from .config import Config, load_config
from .rules import ALL_RULES, Finding, LintContext, run_rules
from .tokens import count_tokens, using_accurate_tokenizer

# ANSI colors, disabled automatically when output is not a TTY.
_COLORS = {
    "error": "\033[31m",
    "warning": "\033[33m",
    "info": "\033[36m",
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
}


def _use_color(stream) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def _paint(text: str, key: str, on: bool) -> str:
    if not on:
        return text
    return f"{_COLORS.get(key, '')}{text}{_COLORS['reset']}"


def discover_files(paths: Sequence[str], patterns: Sequence[str]) -> List[str]:
    """Expand paths into a sorted, de-duplicated list of files to lint.

    A file path is always included. A directory is walked recursively and any
    file matching one of ``patterns`` (by basename) is collected. Hidden
    directories such as ``.git`` and common vendor dirs are skipped.
    """
    skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache"}
    found: List[str] = []
    seen = set()

    def add(p: str) -> None:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap)
            found.append(p)

    for path in paths:
        if os.path.isfile(path):
            add(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                for name in files:
                    if any(fnmatch.fnmatch(name, pat) for pat in patterns):
                        add(os.path.join(root, name))
        else:
            # Treat as a glob relative to cwd.
            import glob as _glob

            for match in sorted(_glob.glob(path, recursive=True)):
                if os.path.isfile(match):
                    add(match)
    found.sort()
    return found


def _format_text(path: str, findings: List[Finding], color: bool) -> str:
    header = _paint(path, "bold", color)
    lines = [header]
    for f in findings:
        loc = _paint(f"{f.line}", "dim", color)
        sev = _paint(f"{f.severity:>7}", f.severity, color)
        lines.append(f"  {loc:>4}  {sev}  {f.message}  {_paint(f.rule, 'dim', color)}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="promptlint",
        description="Lint prompt and agent-instruction files for token budget, "
        "hedging, placeholders, and structure.",
    )
    p.add_argument("paths", nargs="*", default=["."], help="files, directories, or globs")
    p.add_argument("--budget", type=int, default=None, help="token budget per file (0 = off)")
    p.add_argument("--model", default=None, help="tiktoken encoding name (default cl100k_base)")
    p.add_argument("--select", default=None, help="comma-separated rules to run exclusively")
    p.add_argument("--ignore", default=None, help="comma-separated rules to skip")
    p.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    p.add_argument(
        "--max-severity",
        choices=("error", "warning", "info"),
        default="warning",
        help="lowest severity that causes a non-zero exit (default warning)",
    )
    p.add_argument("--stats", action="store_true", help="print token totals per file")
    p.add_argument("--list-rules", action="store_true", help="list available rules and exit")
    p.add_argument("--no-color", action="store_true", help="disable colored output")
    p.add_argument("--version", action="version", version=f"promptlint {__version__}")
    return p


def _severity_rank(sev: str) -> int:
    return {"error": 3, "warning": 2, "info": 1}.get(sev, 0)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_rules:
        for name in ALL_RULES:
            print(name)
        return 0

    paths = args.paths or ["."]
    cfg: Config = load_config(paths[0])

    budget = args.budget if args.budget is not None else cfg.token_budget
    model = args.model or cfg.model
    select = args.select.split(",") if args.select else cfg.select
    ignore = args.ignore.split(",") if args.ignore else cfg.ignore

    files = discover_files(paths, cfg.patterns)
    if not files:
        print("no matching prompt files found", file=sys.stderr)
        return 0

    color = _use_color(sys.stdout) and not args.no_color
    results = {}
    stats = {}
    worst = 0

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"{fp}: cannot read ({exc})", file=sys.stderr)
            continue
        ctx = LintContext(path=fp, text=text, token_budget=budget, model=model)
        findings = run_rules(ctx, select=select or None, ignore=ignore or None)
        results[fp] = findings
        if args.stats:
            stats[fp] = count_tokens(text, model)
        for f in findings:
            worst = max(worst, _severity_rank(f.severity))

    if args.format == "json":
        payload = {
            "version": __version__,
            "accurate_tokenizer": using_accurate_tokenizer(),
            "files": [
                {
                    "path": fp,
                    "tokens": stats.get(fp),
                    "findings": [f.as_dict() for f in fs],
                }
                for fp, fs in results.items()
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        total = 0
        for fp, fs in results.items():
            if fs:
                print(_format_text(fp, fs, color))
                total += len(fs)
            if args.stats:
                tok = stats.get(fp)
                if tok is not None:
                    print(f"  {_paint('tokens', 'dim', color)}  {tok}")
        summary = f"{total} finding(s) across {len(files)} file(s)"
        if not using_accurate_tokenizer():
            summary += "  (token counts estimated; install tiktoken for exact counts)"
        print(_paint(summary, "dim", color))

    threshold = _severity_rank(args.max_severity)
    return 1 if worst >= threshold else 0


if __name__ == "__main__":
    raise SystemExit(main())
