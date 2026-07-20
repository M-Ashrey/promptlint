"""Configuration loading for promptlint.

Config is read from a ``[tool.promptlint]`` table in ``pyproject.toml`` or from
a standalone ``.promptlint.toml`` file. All fields are optional; CLI flags
always override file config.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

try:  # Python 3.11+ ships tomllib in the stdlib.
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised on 3.10
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        tomllib = None  # type: ignore


# File names scanned by default when a directory is given.
DEFAULT_PATTERNS = (
    "*.prompt",
    "*.prompt.md",
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".cursorrules",
    "system_prompt.md",
    "system-prompt.md",
)


@dataclass
class Config:
    """Resolved configuration for a lint run."""

    token_budget: int = 0
    model: str = "cl100k_base"
    select: List[str] = field(default_factory=list)
    ignore: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=lambda: list(DEFAULT_PATTERNS))


def _find_config_file(start: str) -> str | None:
    """Walk upward from ``start`` looking for a config file."""
    cur = os.path.abspath(start)
    if os.path.isfile(cur):
        cur = os.path.dirname(cur)
    while True:
        standalone = os.path.join(cur, ".promptlint.toml")
        if os.path.isfile(standalone):
            return standalone
        pyproject = os.path.join(cur, "pyproject.toml")
        if os.path.isfile(pyproject):
            return pyproject
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def load_config(start: str = ".") -> Config:
    """Load config from the nearest config file, if any.

    Returns defaults when no file is found or the TOML parser is unavailable.
    """
    cfg = Config()
    if tomllib is None:
        return cfg
    path = _find_config_file(start)
    if not path:
        return cfg
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except Exception:
        return cfg

    table = {}
    if path.endswith("pyproject.toml"):
        table = data.get("tool", {}).get("promptlint", {})
    else:
        table = data.get("promptlint", data)

    if not isinstance(table, dict):
        return cfg

    if isinstance(table.get("token_budget"), int):
        cfg.token_budget = table["token_budget"]
    if isinstance(table.get("model"), str):
        cfg.model = table["model"]
    if isinstance(table.get("select"), list):
        cfg.select = [str(x) for x in table["select"]]
    if isinstance(table.get("ignore"), list):
        cfg.ignore = [str(x) for x in table["ignore"]]
    if isinstance(table.get("patterns"), list) and table["patterns"]:
        cfg.patterns = [str(x) for x in table["patterns"]]
    return cfg
