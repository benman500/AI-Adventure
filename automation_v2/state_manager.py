"""Atomic persistence of automation progress for crash-safe resume."""

from __future__ import annotations

import json
import os
from pathlib import Path

from automation_v2.models import AutomationState, Stage, VALID_STAGES


class StateManager:
    """Load and save ``automation_v2/state.json`` with atomic writes."""

    def __init__(self, state_file: Path) -> None:
        """Create a manager bound to a state JSON path."""
        self._state_file = state_file

    @property
    def state_file(self) -> Path:
        """Path to the persisted state file."""
        return self._state_file

    def load(self) -> AutomationState:
        """Load state from disk, or return an idle queued state if missing."""
        if not self._state_file.exists():
            return AutomationState()

        raw = self._state_file.read_text(encoding="utf-8")
        if not raw.strip():
            return AutomationState()

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(
                f"State file must contain a JSON object: {self._state_file}"
            )
        return AutomationState.from_dict(data)

    def save(self, state: AutomationState) -> None:
        """Persist state using a temporary file followed by replacement."""
        if state.current_stage not in VALID_STAGES:
            raise ValueError(f"Invalid stage: {state.current_stage}")

        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), indent=2, ensure_ascii=False)
        payload = payload + "\n"

        temp_path = self._state_file.with_name(
            self._state_file.name + ".tmp"
        )
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, self._state_file)

    def set_stage(
        self,
        state: AutomationState,
        stage: Stage,
        *,
        mark_successful: bool = False,
        error: str | None = None,
    ) -> AutomationState:
        """Update stage fields, optionally mark success, and persist."""
        state.current_stage = stage
        if mark_successful:
            state.last_successful_stage = stage
        if error is not None:
            state.last_error = error
        elif stage not in {"failed", "human_review"}:
            state.last_error = None
        self.save(state)
        return state

    def idle_state(self) -> AutomationState:
        """Return a fresh idle queued state without completed-task history."""
        return AutomationState(current_stage="queued")
