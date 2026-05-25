from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".tox",
}

TEXT_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sql", ".js", ".css", ".html", ".ps1", ".sh", ".bat", ".xml", ".csv", ".tsv", ".env", ".gitignore",
}

DOMAIN_ORDER = [
    "core_runtime",
    "config",
    "database",
    "cli",
    "hub_backend",
    "hub_frontend",
    "project_registry",
    "project_factory",
    "active_project",
    "queue",
    "agents",
    "orchestration",
    "llm_integration",
    "github_integration",
    "documentation_system",
    "validation_evidence",
    "scripts",
    "tests",
    "docs",
    "artifacts",
    "configuration",
    "unknown",
]

STATUS_ORDER = [
    "active",
    "foundation",
    "plan_only",
    "docs_only",
    "test_only",
    "stale_or_aspirational",
    "generated_artifact",
    "unknown",
    "candidate_for_review",
]

ASPIRATIONAL_PATTERNS = (
    "github actions",
    "automation runner",
    "autonomous execution",
    "real agent execution",
    "model routing",
)

PLAN_ONLY_PATTERNS = (
    "plan-only",
    "no execution",
    "read-only",
    "human review required",
)

SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s]+)"),
]


@dataclass(slots=True)
class AssessmentOptions:
    repo_path: Path
    output_path: Path
    format: str
    include_tests: bool
    include_docs: bool
    force: bool


def assess_repository(config: AppConfig, *, options: AssessmentOptions) -> dict[str, Any]:
    repo_path = options.repo_path.resolve()
    output_path = options.output_path.resolve()

    if not repo_path.exists() or not repo_path.is_dir():
        return {"ok": False, "error": "repo_path_not_found", "repo_path": str(repo_path)}

    outputs = _resolve_outputs(output_path)
    existing = [str(path) for path in outputs.values() if path.exists()]
    if existing and not options.force:
        return {
            "ok": False,
            "error": "output_exists",
            "message": "Use --force to overwrite existing assessment outputs.",
            "existing_outputs": sorted(existing),
        }

    files = _collect_files(repo_path, include_tests=options.include_tests, include_docs=options.include_docs)
    text_cache = _build_text_cache(files, repo_path)
    references = _build_references(files, repo_path, text_cache)

    records: list[dict[str, Any]] = []
    for file_path in files:
        record = _build_record(file_path, repo_path, references, text_cache)
        records.append(record)

    records.sort(key=lambda item: item["path"])
    domain_counts = _count_by(records, "architecture_domain")
    status_counts = _count_by(records, "status_classification")
    gaps = _build_gap_register(records, repo_path, text_cache)

    payload = {
        "ok": True,
        "repo_path": str(repo_path),
        "output_path": str(output_path),
        "file_count": len(records),
        "domain_counts": domain_counts,
        "status_counts": status_counts,
        "files": records,
        "gaps": gaps,
    }

    output_path.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    if options.format in {"json", "both"}:
        json_path = outputs["file_map_json"]
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        written.append(str(json_path))

    if options.format in {"markdown", "both"}:
        md_map = _render_repo_file_map_md(payload)
        outputs["file_map_md"].write_text(md_map, encoding="utf-8")
        written.append(str(outputs["file_map_md"]))

        domain_md = _render_domain_map_md(records)
        outputs["domain_map_md"].write_text(domain_md, encoding="utf-8")
        written.append(str(outputs["domain_map_md"]))

        gap_md = _render_gap_register_md(gaps)
        outputs["gap_register_md"].write_text(gap_md, encoding="utf-8")
        written.append(str(outputs["gap_register_md"]))

        summary_md = _render_summary_md(payload, gaps)
        outputs["summary_md"].write_text(summary_md, encoding="utf-8")
        written.append(str(outputs["summary_md"]))

    return {"ok": True, "written_files": sorted(written), "file_count": len(records), "gaps": gaps}


def _resolve_outputs(base: Path) -> dict[str, Path]:
    return {
        "file_map_json": base / "REPO_FILE_MAP.json",
        "file_map_md": base / "REPO_FILE_MAP.md",
        "domain_map_md": base / "ARCHITECTURE_DOMAIN_MAP.md",
        "gap_register_md": base / "GAP_REGISTER_DRAFT.md",
        "summary_md": base / "ASSESSMENT_SUMMARY.md",
    }


def _collect_files(repo_path: Path, *, include_tests: bool, include_docs: bool) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(repo_path.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(repo_path)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if not include_tests and relative.parts and relative.parts[0] == "tests":
            continue
        if not include_docs and relative.parts and relative.parts[0] == "docs":
            continue
        paths.append(path)
    return paths


def _is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    try:
        data = path.read_bytes()[:2048]
    except OSError:
        return False
    return b"\x00" not in data


def _safe_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    return text


def _build_text_cache(files: list[Path], repo_root: Path) -> dict[str, str]:
    cache: dict[str, str] = {}
    for path in files:
        rel = path.relative_to(repo_root).as_posix()
        if _is_probably_text(path):
            cache[rel] = _safe_text(path)
    return cache


def _build_references(files: list[Path], repo_root: Path, text_cache: dict[str, str]) -> dict[str, dict[str, bool]]:
    cli_text = text_cache.get("src/aresforge/cli.py", "")
    hub_text = "\n".join(text for rel, text in text_cache.items() if rel.startswith("src/aresforge/hub/") or rel.startswith("src/aresforge/routing/"))
    tests_text = "\n".join(text for rel, text in text_cache.items() if rel.startswith("tests/"))
    docs_text = "\n".join(text for rel, text in text_cache.items() if rel.startswith("docs/"))

    result: dict[str, dict[str, bool]] = {}
    for path in files:
        rel = path.relative_to(repo_root).as_posix()
        module_hint = rel[:-3].replace("/", ".") if rel.endswith(".py") else ""
        result[rel] = {
            "referenced_by_cli": bool(rel in cli_text or (module_hint and module_hint in cli_text)),
            "referenced_by_hub": bool(rel in hub_text or (module_hint and module_hint in hub_text)),
            "referenced_by_tests": bool(rel in tests_text or (module_hint and module_hint in tests_text)),
            "referenced_by_docs": bool(rel in docs_text or (module_hint and module_hint in docs_text)),
        }
    return result


def _build_record(
    file_path: Path,
    repo_root: Path,
    references: dict[str, dict[str, bool]],
    text_cache: dict[str, str],
) -> dict[str, Any]:
    rel = file_path.relative_to(repo_root).as_posix()
    ext = file_path.suffix.lower()
    file_type = _infer_file_type(file_path)
    text = text_cache.get(rel, "")
    line_count = len(text.splitlines()) if rel in text_cache else None

    domain = _infer_domain(rel)
    purpose = _infer_purpose(rel, text)
    status, reasons = _classify_status(rel, domain, text)

    imports: list[str] = []
    classes: list[str] = []
    functions: list[str] = []
    cli_commands_detected: list[str] = []
    hub_routes_detected: list[str] = []

    if ext == ".py" and text:
        imports, classes, functions = _parse_python_symbols(text)
        cli_commands_detected = sorted(set(re.findall(r'add_parser\("([^"]+)"', text)))
        hub_routes_detected = sorted(set(re.findall(r'@app\.(?:get|post|put|delete|patch)\("([^"]+)"', text)))
    elif ext in {".js", ".ts"} and text:
        hub_routes_detected = sorted(set(re.findall(r"['\"](/api/[^'\"]+)['\"]", text)))

    refs = references.get(rel, {
        "referenced_by_cli": False,
        "referenced_by_hub": False,
        "referenced_by_tests": False,
        "referenced_by_docs": False,
    })

    notes: list[str] = []
    if rel.startswith(".aresforge/") and text and "[REDACTED]" in text:
        notes.append("Sensitive-looking values were redacted in assessment output.")

    return {
        "path": rel,
        "extension": ext,
        "file_type": file_type,
        "size_bytes": file_path.stat().st_size,
        "line_count": line_count,
        "architecture_domain": domain,
        "inferred_purpose": purpose,
        "status_classification": status,
        "reasons": reasons,
        "referenced_by_cli": refs["referenced_by_cli"],
        "referenced_by_hub": refs["referenced_by_hub"],
        "referenced_by_tests": refs["referenced_by_tests"],
        "referenced_by_docs": refs["referenced_by_docs"],
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "cli_commands_detected": cli_commands_detected,
        "hub_routes_detected": hub_routes_detected,
        "notes": notes,
    }


def _infer_file_type(path: Path) -> str:
    if _is_probably_text(path):
        return "text"
    return "binary"


def _infer_domain(rel: str) -> str:
    if rel == "src/aresforge/cli.py":
        return "cli"
    if rel.startswith("src/aresforge/hub/static/"):
        return "hub_frontend"
    if rel.startswith("src/aresforge/hub/"):
        return "hub_backend"
    if rel.startswith("src/aresforge/routing/"):
        return "hub_backend"
    if rel.startswith("src/aresforge/db/") or rel.startswith("migrations/"):
        return "database"
    if rel.startswith("src/aresforge/integrations/"):
        return "llm_integration"
    if rel.startswith("src/aresforge/operator/github"):
        return "github_integration"
    if rel.startswith("src/aresforge/operator/local_project_factory"):
        return "project_factory"
    if rel.startswith("src/aresforge/operator/managed_project_registry"):
        return "project_registry"
    if rel.startswith("src/aresforge/operator/local_active_project"):
        return "active_project"
    if rel.startswith("src/aresforge/operator/local_project_queue"):
        return "queue"
    if rel.startswith("src/aresforge/operator/local_agent") or rel.startswith("src/aresforge/operator/agent_"):
        return "agents"
    if rel.startswith("src/aresforge/operator/"):
        return "orchestration"
    if rel.startswith("src/aresforge/config.py"):
        return "config"
    if rel.startswith("src/aresforge/validation/"):
        return "validation_evidence"
    if rel.startswith("scripts/"):
        return "scripts"
    if rel.startswith("tests/"):
        return "tests"
    if rel.startswith("docs/"):
        return "docs"
    if rel.startswith("artifacts/"):
        return "artifacts"
    if rel.startswith("config/") or rel.endswith(".toml") or rel.endswith(".yml") or rel.endswith(".yaml"):
        return "configuration"
    if rel.startswith("src/aresforge/"):
        return "core_runtime"
    return "unknown"


def _infer_purpose(rel: str, text: str) -> str:
    if rel.startswith("tests/"):
        return "Automated verification coverage."
    if rel.startswith("docs/"):
        return "Project documentation and design narrative."
    if rel.startswith("src/aresforge/operator/"):
        return "Local operator workflow/inspection logic."
    if rel == "src/aresforge/cli.py":
        return "CLI command registration and dispatch entrypoint."
    if rel.startswith("src/aresforge/hub/"):
        return "Hub backend/frontend serving and route handling."
    if rel.startswith("src/aresforge/db/"):
        return "Database connectivity, migrations, and repositories."
    if text:
        first_line = text.splitlines()[0].strip()
        if first_line:
            return first_line[:120]
    return "Purpose inference unavailable."


def _classify_status(rel: str, domain: str, text: str) -> tuple[str, list[str]]:
    reasons: list[str] = []
    lowered = text.lower()

    if rel.startswith("tests/"):
        return "test_only", ["Located under tests/. "]
    if rel.startswith("docs/"):
        if any(pattern in lowered for pattern in ASPIRATIONAL_PATTERNS):
            return "stale_or_aspirational", ["Documentation contains capability claims that may be aspirational."]
        return "docs_only", ["Located under docs/. "]
    if rel.startswith("artifacts/"):
        return "generated_artifact", ["Located under artifacts/. "]
    if any(pattern in lowered for pattern in PLAN_ONLY_PATTERNS):
        return "plan_only", ["Contains plan-only or non-execution boundary language."]
    if domain in {"cli", "hub_backend", "core_runtime", "database", "config"}:
        return "foundation", ["Core runtime/entrypoint component."]
    if domain in {"orchestration", "project_registry", "project_factory", "active_project", "queue", "agents", "llm_integration", "github_integration"}:
        return "active", ["Operational source module in active code tree."]
    if domain == "unknown":
        return "candidate_for_review", ["Domain could not be inferred confidently."]
    return "unknown", ["No strong classification signal matched."]


def _parse_python_symbols(text: str) -> tuple[list[str], list[str], list[str]]:
    imports: set[str] = set()
    classes: set[str] = set()
    functions: set[str] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], [], []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.add(f"{module}.{alias.name}" if module else alias.name)
        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.add(node.name)
    return sorted(imports), sorted(classes), sorted(functions)


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _build_gap_register(records: list[dict[str, Any]], repo_root: Path, text_cache: dict[str, str]) -> list[dict[str, str]]:
    path_set = {record["path"] for record in records}
    docs_text = "\n".join(text for rel, text in text_cache.items() if rel.startswith("docs/"))
    orchestration_text = "\n".join(text for rel, text in text_cache.items() if rel.startswith("src/aresforge/operator/"))

    gaps: list[dict[str, str]] = []

    workflows_exist = any(path.startswith(".github/workflows/") for path in path_set)
    if not workflows_exist:
        gaps.append({"id": "no_github_workflows", "finding": "No GitHub workflow files found under .github/workflows.", "severity": "medium"})

    if "plan-only" in orchestration_text.lower() and "execute" not in orchestration_text.lower():
        gaps.append({"id": "no_real_agent_runtime", "finding": "No real agent execution runtime detected when orchestration appears plan-only.", "severity": "high"})

    has_ollama = any(path.startswith("src/aresforge/integrations/ollama") for path in path_set)
    has_multi_provider = any("model_registry" in path or "routing" in path for path in path_set if path.startswith("src/"))
    if has_ollama and not has_multi_provider:
        gaps.append({"id": "llm_abstraction_gap", "finding": "Direct Ollama integration appears present without clear multi-provider LLM abstraction.", "severity": "medium"})

    if any(pattern in docs_text.lower() for pattern in ASPIRATIONAL_PATTERNS) and not workflows_exist:
        gaps.append({"id": "docs_claim_runtime_gap", "finding": "Docs claim automation/runtime capabilities not backed by implementation evidence.", "severity": "high"})

    has_db = any(path.startswith("src/aresforge/db/") for path in path_set)
    has_file_state = any(path.startswith(".aresforge/") or "state" in path for path in path_set)
    if has_db and has_file_state:
        gaps.append({"id": "state_strategy_unclear", "finding": "File-backed state and database-backed state both exist; strategy boundary may be unclear.", "severity": "medium"})

    has_project_factory = any("project_factory" in path for path in path_set)
    if has_project_factory and "apply" not in orchestration_text.lower():
        gaps.append({"id": "project_factory_execution_gap", "finding": "Project factory exists but execution/apply lifecycle appears incomplete or approval-only.", "severity": "medium"})

    has_hub = any(path.startswith("src/aresforge/hub/") for path in path_set)
    if has_hub and "run lifecycle" not in docs_text.lower() and "run" not in orchestration_text.lower():
        gaps.append({"id": "hub_execution_console_gap", "finding": "Hub exists but does not clearly expose a complete run lifecycle execution console.", "severity": "medium"})

    return gaps


def _render_repo_file_map_md(payload: dict[str, Any]) -> str:
    lines = ["# REPO_FILE_MAP", "", f"- Repo path: `{payload['repo_path']}`", f"- File count: {payload['file_count']}", ""]
    lines.append("## Summary by domain")
    for domain, count in sorted(payload["domain_counts"].items()):
        lines.append(f"- {domain}: {count}")
    lines.append("")
    lines.append("## Summary by classification")
    for status, count in sorted(payload["status_counts"].items()):
        lines.append(f"- {status}: {count}")
    lines.append("")
    lines.append("## File inventory")
    lines.append("| path | domain | classification | purpose | refs (cli/hub/tests/docs) |")
    lines.append("|---|---|---|---|---|")
    for record in payload["files"]:
        refs = f"{int(record['referenced_by_cli'])}/{int(record['referenced_by_hub'])}/{int(record['referenced_by_tests'])}/{int(record['referenced_by_docs'])}"
        purpose = str(record["inferred_purpose"]).replace("|", "\\|")
        lines.append(f"| `{record['path']}` | {record['architecture_domain']} | {record['status_classification']} | {purpose} | {refs} |")
    lines.append("")
    lines.append("## Unknown and candidate for review")
    for record in payload["files"]:
        if record["status_classification"] in {"unknown", "candidate_for_review"}:
            lines.append(f"- `{record['path']}` ({record['status_classification']})")
    lines.append("")
    return "\n".join(lines)


def _render_domain_map_md(records: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {domain: [] for domain in DOMAIN_ORDER}
    for record in records:
        grouped.setdefault(record["architecture_domain"], []).append(record)

    lines = ["# ARCHITECTURE_DOMAIN_MAP", ""]
    for domain in DOMAIN_ORDER:
        items = sorted(grouped.get(domain, []), key=lambda item: item["path"])
        lines.append(f"## {domain}")
        if not items:
            lines.append("- No files detected in this domain.")
            lines.append("- Missing/weak signals: no concrete implementation footprint found.")
            lines.append("")
            continue
        for item in items:
            lines.append(f"- `{item['path']}`: {item['inferred_purpose']}")
        weak = [item["path"] for item in items if item["status_classification"] in {"unknown", "candidate_for_review", "plan_only"}]
        if weak:
            lines.append(f"- Missing/weak signals: {', '.join(f'`{path}`' for path in weak[:8])}")
        else:
            lines.append("- Missing/weak signals: none obvious from static scan.")
        lines.append("")
    return "\n".join(lines)


def _render_gap_register_md(gaps: list[dict[str, str]]) -> str:
    lines = ["# GAP_REGISTER_DRAFT", "", "Draft findings from local read-only assessment:", ""]
    for gap in gaps:
        lines.append(f"- [{gap['severity']}] {gap['id']}: {gap['finding']}")
    lines.append("")
    return "\n".join(lines)


def _render_summary_md(payload: dict[str, Any], gaps: list[dict[str, str]]) -> str:
    lines = [
        "# ASSESSMENT_SUMMARY",
        "",
        "## Executive summary",
        f"Assessed {payload['file_count']} files using a deterministic local read-only scan.",
        "",
        "## What is real and active",
        "Core source trees under `src/aresforge/`, CLI wiring, and tests/docs/artifacts were inventoried with references and symbol extraction.",
        "",
        "## What is plan-only",
        "Files with explicit plan-only/non-execution language were flagged for plan-only status.",
        "",
        "## What appears missing",
    ]
    for gap in gaps:
        lines.append(f"- {gap['finding']}")
    lines.extend([
        "",
        "## Recommended next audit/reconciliation steps",
        "1. Review candidate-for-review and stale/aspirational docs against implementation files.",
        "2. Confirm execution lifecycle boundaries for orchestration, hub, and project factory modules.",
        "3. Resolve architecture gaps into approved implementation roadmap items.",
        "",
        "## Safety note",
        "This command performs local-only repository assessment. It does not mutate GitHub state and does not execute agents.",
        "",
    ])
    return "\n".join(lines)
