"""Token estimation utilities.

Uses ``tiktoken`` when it is installed for accurate counts; otherwise falls
back to a heuristic that approximates typical byte-pair encodings closely
enough for budgeting decisions.
"""
from __future__ import annotations

import re

_PIECE_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def _heuristic_tokens(text: str) -> int:
    """Approximate token count without any third-party dependency.

    Alphanumeric runs are split into ~4-character sub-word chunks (the rough
    average for English BPE vocabularies); standalone punctuation counts as a
    single token each.
    """
    total = 0
    for piece in _PIECE_RE.findall(text):
        if piece.isalnum():
            total += max(1, (len(piece) + 3) // 4)
        else:
            total += 1
    return total


def using_accurate_tokenizer() -> bool:
    """Return True if the accurate ``tiktoken`` backend is available."""
    try:
        import tiktoken  # noqa: F401
    except Exception:
        return False
    return True


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Return an estimated token count for ``text``.

    ``model`` is a ``tiktoken`` encoding name and is ignored by the heuristic
    fallback.
    """
    if not text:
        return 0
    try:
        import tiktoken  # type: ignore

        try:
            enc = tiktoken.get_encoding(model)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return _heuristic_tokens(text)
