"""Tiny pytest helpers with no application imports."""

from __future__ import annotations


def strip_retained_keyword_quotes(keyword: str | None) -> str | None:
    """Remove one matching quote layer retained by Windows ``shlex`` (posix=False).

    Orchestrator focused entries like ``-k "character and creation"`` can arrive with
    the quote characters still inside the expression. Pytest 8+ rejects that as a
    string literal and exits with code 4 before any tests run.
    """

    if keyword is None or len(keyword) < 2:
        return keyword
    if keyword[0] == keyword[-1] and keyword[0] in "\"'":
        return keyword[1:-1]
    return keyword
