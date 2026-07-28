"""Shared pytest hooks for the test suite."""

from __future__ import annotations

from typing import Any

import pytest

from tests.pytest_keyword_utils import strip_retained_keyword_quotes


def _normalize_keyword_option(config: Any) -> None:
    """Apply quote stripping to ``config.option.keyword`` when present."""

    current = getattr(config.option, "keyword", None)
    normalized = strip_retained_keyword_quotes(current)
    if normalized != current:
        config.option.keyword = normalized


def pytest_configure(config: Any) -> None:
    """Normalize ``-k`` as early as possible after option parsing."""

    _normalize_keyword_option(config)


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Normalize ``-k`` again immediately before keyword deselection."""

    _normalize_keyword_option(config)
