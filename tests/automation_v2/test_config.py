"""Tests for config validation and package smoke imports."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from automation_v2.config import load_config


ROOT = Path(__file__).resolve().parents[2]


def test_load_config_defaults() -> None:
    """Default configuration validates and points at the repo root."""
    config = load_config(ROOT)
    assert config.repository_root == ROOT.resolve()
    assert config.tasks_file.name == "tasks.json"
    assert config.max_changed_files >= 1
    assert "OPENAI" in config.openai_model_env_var


def test_invalid_config_raises() -> None:
    """Negative timeouts fail validation at startup."""
    with patch.dict(os.environ, {"AUTOMATION_CURSOR_TIMEOUT_SECONDS": "0"}):
        try:
            load_config(ROOT)
            raised = False
        except ValueError:
            raised = True
    assert raised is True
