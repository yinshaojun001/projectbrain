"""Local privacy policy controls for ProjectBrain runtime output."""

from __future__ import annotations

import copy
import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SOURCE_SNIPPET_KEYS = {"body", "source_body", "source_code", "snippet", "text"}
POLICY_FILENAMES = (".projectbrain-policy.json", ".projectbrain-policy.yml", ".projectbrain-policy.yaml")


@dataclass(frozen=True)
class ProjectBrainPolicy:
    """Output policy loaded from a local project policy file."""

    deny_paths: list[str] = field(default_factory=list)
    max_items_per_section: int | None = None
    max_recommended_files: int | None = None
    max_recommended_tests: int | None = None
    include_source_snippets: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectBrainPolicy":
        output_limits = data.get("output_limits", {})
        if not isinstance(output_limits, dict):
            output_limits = {}
        return cls(
            deny_paths=_as_string_list(data.get("deny_paths", [])),
            max_items_per_section=_positive_int_or_none(
                data.get("max_items_per_section", output_limits.get("max_items_per_section"))
            ),
            max_recommended_files=_positive_int_or_none(
                data.get("max_recommended_files", output_limits.get("max_recommended_files"))
            ),
            max_recommended_tests=_positive_int_or_none(
                data.get("max_recommended_tests", output_limits.get("max_recommended_tests"))
            ),
            include_source_snippets=bool(data.get("include_source_snippets", False)),
        )


@dataclass(frozen=True)
class LoadedProjectBrainPolicy:
    """A policy plus the local file it was loaded from."""

    policy: ProjectBrainPolicy
    source_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_found": self.source_path is not None,
            "source_path": self.source_path,
            "policy": {
                "deny_paths": self.policy.deny_paths,
                "output_limits": {
                    "max_items_per_section": self.policy.max_items_per_section,
                    "max_recommended_files": self.policy.max_recommended_files,
                    "max_recommended_tests": self.policy.max_recommended_tests,
                },
                "include_source_snippets": self.policy.include_source_snippets,
            },
            "summary": {
                "deny_path_count": len(self.policy.deny_paths),
                "has_output_caps": any(
                    limit is not None
                    for limit in (
                        self.policy.max_items_per_section,
                        self.policy.max_recommended_files,
                        self.policy.max_recommended_tests,
                    )
                ),
                "source_snippets_enabled": self.policy.include_source_snippets,
            },
        }


def load_policy_for_project(project_path: str | Path) -> ProjectBrainPolicy:
    """Load a project-local policy file if present."""

    return load_policy_with_source(project_path).policy


def load_policy_with_source(project_path: str | Path) -> LoadedProjectBrainPolicy:
    """Load a project-local policy file and report where it came from."""

    root = Path(project_path)
    for filename in POLICY_FILENAMES:
        path = root / filename
        if path.exists():
            return LoadedProjectBrainPolicy(
                policy=ProjectBrainPolicy.from_dict(_read_policy_file(path)),
                source_path=str(path),
            )
    return LoadedProjectBrainPolicy(policy=ProjectBrainPolicy())


def inspect_policy_for_project(project_path: str | Path) -> dict[str, Any]:
    return load_policy_with_source(project_path).to_dict()


def apply_output_policy(data: dict[str, Any], policy: ProjectBrainPolicy) -> dict[str, Any]:
    """Return an artifact copy with deny-path and output-limit rules applied."""

    filtered = copy.deepcopy(data)
    _strip_source_snippets(filtered, include_source_snippets=policy.include_source_snippets)
    _filter_denied_paths(filtered, policy)
    _apply_caps(filtered, policy)
    return filtered


def _read_policy_file(path: Path) -> dict[str, Any]:
    contents = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(contents)
    else:
        data = _parse_simple_yaml(contents)
    if not isinstance(data, dict):
        raise ValueError(f"ProjectBrain policy must be an object: {path}")
    return data


def _parse_simple_yaml(contents: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in contents.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith(" ") and current_list_key and line.strip().startswith("- "):
            data.setdefault(current_list_key, []).append(_parse_scalar(line.strip()[2:]))
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value == "":
            data[key] = []
            current_list_key = key
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [_parse_scalar(item.strip()) for item in value[1:-1].split(",") if item.strip()]
        else:
            data[key] = _parse_scalar(value)
    return data


def _parse_scalar(value: str) -> Any:
    normalized = value.strip().strip('"').strip("'")
    if normalized.lower() in {"true", "false"}:
        return normalized.lower() == "true"
    try:
        return int(normalized)
    except ValueError:
        return normalized


def _filter_denied_paths(value: Any, policy: ProjectBrainPolicy) -> bool:
    if isinstance(value, dict):
        if _dict_has_denied_path(value, policy):
            return True
        for key in list(value.keys()):
            if _filter_denied_paths(value[key], policy):
                del value[key]
        return False
    if isinstance(value, list):
        value[:] = [item for item in value if not _filter_denied_paths(item, policy)]
    return False


def _dict_has_denied_path(item: dict[str, Any], policy: ProjectBrainPolicy) -> bool:
    for candidate in _path_candidates(item):
        if _is_denied_path(candidate, policy.deny_paths):
            return True
    return False


def _path_candidates(item: dict[str, Any]) -> list[str]:
    candidates = []
    for key in ("file", "file_path", "path"):
        value = item.get(key)
        if isinstance(value, str):
            candidates.append(value)
    locator = item.get("locator")
    if isinstance(locator, dict) and isinstance(locator.get("file"), str):
        candidates.append(locator["file"])
    properties = item.get("properties")
    if isinstance(properties, dict) and isinstance(properties.get("file_path"), str):
        candidates.append(properties["file_path"])
    return candidates


def _is_denied_path(path: str, deny_paths: list[str]) -> bool:
    normalized_path = _normalize_path(path)
    for pattern in deny_paths:
        normalized_pattern = _normalize_path(pattern)
        if (
            fnmatch.fnmatch(normalized_path, normalized_pattern)
            or normalized_path.startswith(normalized_pattern.rstrip("/") + "/")
            or normalized_pattern in normalized_path
        ):
            return True
    return False


def _strip_source_snippets(value: Any, *, include_source_snippets: bool) -> None:
    if include_source_snippets:
        return
    if isinstance(value, dict):
        for key in list(value.keys()):
            if key in SOURCE_SNIPPET_KEYS:
                del value[key]
            else:
                _strip_source_snippets(value[key], include_source_snippets=include_source_snippets)
    elif isinstance(value, list):
        for item in value:
            _strip_source_snippets(item, include_source_snippets=include_source_snippets)


def _apply_caps(data: dict[str, Any], policy: ProjectBrainPolicy) -> None:
    if policy.max_items_per_section is not None:
        for section in data.get("sections", []):
            items = section.get("items") if isinstance(section, dict) else None
            if isinstance(items, list):
                del items[policy.max_items_per_section :]
    _cap_list(data, "recommended_files", policy.max_recommended_files)
    _cap_list(data, "recommended_tests", policy.max_recommended_tests)


def _cap_list(data: dict[str, Any], key: str, limit: int | None) -> None:
    if limit is None:
        return
    value = data.get(key)
    if isinstance(value, list):
        del value[limit:]


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    raw_values = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in raw_values if str(item).strip()]


def _positive_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    normalized = int(value)
    if normalized < 0:
        raise ValueError("ProjectBrain policy limits must be non-negative")
    return normalized


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/")
