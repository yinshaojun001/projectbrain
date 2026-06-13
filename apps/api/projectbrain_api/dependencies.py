"""Runtime dependencies for the ProjectBrain API."""

from __future__ import annotations

import os

from projectbrain_runtime.repository import JsonProjectBrainRepository
from projectbrain_runtime.service import ProjectBrainRuntime


def build_runtime(store_root: str | None = None) -> ProjectBrainRuntime:
    root = store_root or os.environ.get("PROJECTBRAIN_STORE_ROOT", ".projectbrain")
    return ProjectBrainRuntime(JsonProjectBrainRepository(root))
