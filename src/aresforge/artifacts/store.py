from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "artifact"


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True, slots=True)
class ArtifactBundle:
    markdown_path: Path
    json_path: Path
    payload: dict[str, Any]


def write_markdown_json_bundle(
    base_dir: Path,
    *,
    title: str,
    markdown: str,
    payload: dict[str, Any],
) -> ArtifactBundle:
    base_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{_timestamp()}-{_slugify(title)}"
    markdown_path = base_dir / f"{stem}.md"
    json_path = base_dir / f"{stem}.json"
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return ArtifactBundle(markdown_path=markdown_path, json_path=json_path, payload=payload)
