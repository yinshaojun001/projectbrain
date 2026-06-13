"""Local Git diff helpers for ProjectBrain."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitDiffSelection:
    """Select which local Git diff should be inspected."""

    staged: bool = False
    from_ref: str | None = None
    to_ref: str | None = None
    last_commit: bool = False

    def label(self) -> str:
        if self.staged:
            return "staged"
        if self.last_commit:
            return "last_commit"
        if self.from_ref or self.to_ref:
            return f"{self.from_ref or 'HEAD'}..{self.to_ref or 'working-tree'}"
        return "working_tree"


def changed_files_for_selection(repo_path: str | Path, selection: GitDiffSelection) -> list[str]:
    """Return changed file paths from local Git without reading file contents."""

    _validate_selection(selection)
    path = Path(repo_path)
    command = ["git", "-C", str(path), "diff", "--name-only"]

    if selection.staged:
        command.append("--cached")
    elif selection.last_commit:
        command.extend(["HEAD~1", "HEAD"])
    elif selection.from_ref and selection.to_ref:
        command.extend([selection.from_ref, selection.to_ref])
    elif selection.from_ref:
        command.append(selection.from_ref)
    elif selection.to_ref:
        command.extend(["HEAD", selection.to_ref])

    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})


def _validate_selection(selection: GitDiffSelection) -> None:
    selected_modes = [
        selection.staged,
        selection.last_commit,
        bool(selection.from_ref or selection.to_ref),
    ]
    if sum(1 for selected in selected_modes if selected) > 1:
        raise ValueError("Choose only one Git diff selection mode: staged, last_commit, or from/to refs")
