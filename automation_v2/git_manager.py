"""Git operations for automation_v2.

Never pushes, merges, resets hard, deletes branches, or rewrites history.
"""

from __future__ import annotations

from pathlib import Path

from automation_v2.models import CommandResult
from automation_v2.process_runner import run_command


class GitError(RuntimeError):
    """Raised when a required git operation fails."""


class GitManager:
    """Safe git helpers scoped to the repository root."""

    def __init__(self, repository_root: Path) -> None:
        """Bind git operations to ``repository_root``."""
        self._root = repository_root

    def _git(self, *args: str, timeout: float | None = 120) -> CommandResult:
        return run_command(
            ["git", *args],
            cwd=self._root,
            timeout=timeout,
        )

    def current_branch(self) -> str:
        """Return the current branch name."""
        result = self._git("branch", "--show-current")
        if result.returncode != 0:
            raise GitError(result.stderr or "Failed to read current branch")
        return result.stdout.strip()

    def verify_agent_branch(self) -> str:
        """Ensure automation runs only on a branch beginning with ``agent/``."""
        branch = self.current_branch()
        if not branch.startswith("agent/"):
            raise GitError(
                "Automation must run on an agent branch. "
                f"Current branch: {branch or '(detached HEAD)'}"
            )
        return branch

    def is_worktree_clean(self) -> bool:
        """Return True when ``git status --porcelain`` is empty."""
        result = self._git("status", "--porcelain")
        if result.returncode != 0:
            raise GitError(result.stderr or "Failed to read git status")
        return result.stdout.strip() == ""

    def require_clean_worktree(self) -> None:
        """Raise when the worktree has uncommitted changes."""
        if not self.is_worktree_clean():
            raise GitError(
                "Git has uncommitted changes. "
                "Commit or stash them before starting."
            )

    def list_changed_files(self) -> list[str]:
        """List unstaged and staged changed file paths (normalized)."""
        # Include both staged and unstaged tracked/untracked changes relevant
        # to review, without deleting anything.
        names: set[str] = set()

        for args in (
            ("diff", "--name-only"),
            ("diff", "--cached", "--name-only"),
            ("ls-files", "--others", "--exclude-standard"),
        ):
            result = self._git(*args)
            if result.returncode != 0:
                raise GitError(
                    result.stderr or f"git {' '.join(args)} failed"
                )
            for line in result.stdout.splitlines():
                cleaned = line.strip().replace("\\", "/")
                if cleaned:
                    names.add(cleaned)

        return sorted(names)

    def collect_diff(self) -> dict[str, str | list[str]]:
        """Collect diff stat, a truncated diff, and changed file names."""
        stat = self._git("diff", "--stat", "HEAD")
        if stat.returncode != 0:
            # Fall back to unstaged-only stat if HEAD comparison fails.
            stat = self._git("diff", "--stat")

        diff = self._git(
            "diff",
            "HEAD",
            "--",
            ".",
            ":(exclude)automation_v2/runs",
            ":(exclude)automation/runs",
        )
        if diff.returncode != 0:
            diff = self._git(
                "diff",
                "--",
                ".",
                ":(exclude)automation_v2/runs",
                ":(exclude)automation/runs",
            )

        return {
            "stat": stat.stdout or "",
            "diff": (diff.stdout or "")[-60000:],
            "changed_files": self.list_changed_files(),
        }

    def stage_all(self) -> None:
        """Stage all changes in the worktree (never pushes)."""
        result = self._git("add", "-A")
        if result.returncode != 0:
            raise GitError(result.stderr or "git add failed")

    def commit(self, message: str) -> None:
        """Create a commit on the current branch. Never pushes or merges."""
        if not message.strip():
            raise GitError("Commit message must not be empty")
        result = self._git("commit", "-m", message)
        if result.returncode != 0:
            raise GitError(result.stderr or "git commit failed")

    def commit_approved_task(self, task_id: str, title: str) -> None:
        """Stage and commit approved work for ``task_id``."""
        self.stage_all()
        self.commit(f"agent: {task_id} {title}")
