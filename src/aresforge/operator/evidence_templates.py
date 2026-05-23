from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


SECTION_ORDER: tuple[str, ...] = (
    "summary",
    "issue",
    "pr",
    "branch_commit",
    "files_changed",
    "validation",
    "safety_posture",
    "notes_warnings",
)


@dataclass(frozen=True)
class EvidenceTemplateSection:
    title: str
    lines: tuple[str, ...]


def render_markdown_sections(sections: Iterable[EvidenceTemplateSection]) -> str:
    rendered: list[str] = []
    for section in sections:
        rendered.append(section.title)
        rendered.append("")
        rendered.extend(section.lines if section.lines else ("- <none>",))
        rendered.append("")
    return "\n".join(rendered).rstrip() + "\n"

