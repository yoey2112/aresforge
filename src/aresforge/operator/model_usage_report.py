from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_contract import RUNS_DIR_RELATIVE
from aresforge.operator.codex_dispatch_runner import RUN_STATE_FILE_NAME, unavailable_token_usage

MODEL_USAGE_REPORT_VERSION = "m89.1"

_BOUNDARY_CONFIRMATIONS = (
    "M89 model usage reporting is local-only.",
    "Codex dispatch run states are read from local files only.",
    "Local LLM advisory and coding draft metadata are read from local artifacts only.",
    "No network calls are made.",
    "No provider or model is invoked.",
    "No repository files are mutated unless an explicit --output report path is supplied.",
    "No queue state is mutated.",
    "No queue item is completed.",
    "No automatic next-item execution.",
    "No GitHub API calls.",
    "No gh calls.",
    "No issues, PRs, workflows, daemons, watchers, schedulers, or external workflow behavior.",
)


def inspect_model_usage_report(
    config: AppConfig,
    *,
    output: str | Path | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_model_usage_report(config)
    markdown = _render_markdown(payload)
    if output:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = (config.repo_root / output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2) + "\n" if output_format == "json" else markdown + "\n", encoding="utf-8")
        return {
            "command": "inspect-model-usage-report",
            "ok": bool(payload.get("ok", False)),
            "local_only": True,
            "format": output_format,
            "wrote_output_file": True,
            "output_path": str(output_path),
            "payload": payload,
        }
    return _stdout_result("inspect-model-usage-report", payload, output_format, markdown)


def build_model_usage_report(config: AppConfig) -> dict[str, Any]:
    codex = _summarize_codex_dispatch_runs(config)
    advisory = _summarize_local_llm_artifacts(
        config.artifact_root / "local_llm_advisory" / "generated",
        artifact_type="local_llm_advisory",
    )
    drafts = _summarize_local_llm_artifacts(
        config.artifact_root / "local_coding_drafts" / "generated",
        artifact_type="local_coding_draft",
    )
    missing_usage_count = codex["token_usage"]["unavailable_count"] + advisory["missing_token_usage_count"] + drafts["missing_token_usage_count"]
    return {
        "ok": True,
        "local_only": True,
        "read_only": True,
        "report_name": "model_usage_token_accounting_report",
        "report_version": MODEL_USAGE_REPORT_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "codex_dispatch": codex,
        "local_llm_advisory": advisory,
        "local_coding_drafts": drafts,
        "missing_usage_metadata": {
            "total_missing_or_unavailable_count": missing_usage_count,
            "codex_unavailable_token_usage_count": codex["token_usage"]["unavailable_count"],
            "local_llm_advisory_missing_token_usage_count": advisory["missing_token_usage_count"],
            "local_coding_draft_missing_token_usage_count": drafts["missing_token_usage_count"],
            "extraction_errors": codex["token_usage"]["extraction_errors"],
        },
        "safety_boundary": {
            "local_only": True,
            "read_only_by_default": True,
            "network_calls_allowed": False,
            "provider_invocation_allowed": False,
            "repo_mutation_allowed": False,
            "queue_mutation_allowed": False,
            "queue_completion_allowed": False,
            "automatic_next_item_execution_allowed": False,
            "github_api_allowed": False,
            "gh_allowed": False,
            "external_workflow_allowed": False,
        },
        "next_safe_action": "Use this local usage summary for future routing/cost review; do not execute or advance queue items from this report.",
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _summarize_codex_dispatch_runs(config: AppConfig) -> dict[str, Any]:
    runs_root = (config.repo_root / RUNS_DIR_RELATIVE).resolve()
    runs: list[dict[str, Any]] = []
    invalid_run_states: list[dict[str, str]] = []
    total_tokens = 0
    available_count = 0
    unavailable_count = 0
    extraction_errors: list[dict[str, str]] = []
    model_groups: Counter[str] = Counter()

    if runs_root.exists():
        for path in sorted(runs_root.glob(f"*/{RUN_STATE_FILE_NAME}")):
            state = _read_json(path)
            if not isinstance(state, dict):
                invalid_run_states.append({"run_state_path": str(path), "error_summary": "run_state_json_invalid_or_not_object"})
                continue
            usage = state.get("token_usage")
            if not isinstance(usage, dict):
                usage = unavailable_token_usage("token_usage field is not present in this run_state.json; it may predate M79.3.")
            model = _metadata_value(usage.get("model") or state.get("model") or state.get("codex_model"))
            provider = _metadata_value(usage.get("provider") or state.get("provider") or state.get("codex_provider"))
            reasoning_effort = _metadata_value(usage.get("reasoning_effort") or state.get("reasoning_effort") or state.get("codex_reasoning_effort"))
            available = bool(usage.get("available", False))
            tokens = usage.get("total_tokens")
            if available and isinstance(tokens, int):
                available_count += 1
                total_tokens += tokens
            else:
                unavailable_count += 1
                error_summary = str(usage.get("extraction_error", "")).strip()
                if error_summary:
                    extraction_errors.append({"run_id": str(state.get("run_id", "")).strip(), "error_summary": error_summary})
            model_groups[_group_key(provider, model, reasoning_effort)] += 1
            runs.append(
                {
                    "run_id": str(state.get("run_id", "")).strip(),
                    "item_id": str(state.get("item_id", "")).strip(),
                    "dispatch_state": str(state.get("dispatch_state", "")).strip(),
                    "model": model,
                    "provider": provider,
                    "reasoning_effort": reasoning_effort,
                    "token_usage_available": available,
                    "total_tokens": tokens if isinstance(tokens, int) else None,
                    "token_usage_source": str(usage.get("source", "")).strip(),
                    "extraction_error": str(usage.get("extraction_error", "")).strip(),
                    "run_state_path": str(path),
                }
            )

    return {
        "runs_root": str(runs_root),
        "run_count": len(runs),
        "invalid_run_state_count": len(invalid_run_states),
        "invalid_run_states": invalid_run_states,
        "token_usage": {
            "available_count": available_count,
            "unavailable_count": unavailable_count,
            "total_tokens": total_tokens,
            "extraction_error_count": len(extraction_errors),
            "extraction_errors": extraction_errors,
        },
        "model_provider_reasoning_effort_counts": _counter_entries(model_groups),
        "runs": runs,
    }


def _summarize_local_llm_artifacts(artifact_dir: Path, *, artifact_type: str) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []
    invalid_metadata: list[dict[str, str]] = []
    status_counts: Counter[str] = Counter()
    model_groups: Counter[str] = Counter()
    missing_token_usage_count = 0

    if artifact_dir.exists():
        for path in sorted(artifact_dir.glob("*-metadata.json")):
            metadata = _read_json(path)
            if not isinstance(metadata, dict):
                invalid_metadata.append({"metadata_path": str(path), "error_summary": "metadata_json_invalid_or_not_object"})
                continue
            provider_metadata = metadata.get("provider_model_metadata", {})
            if not isinstance(provider_metadata, dict):
                provider_metadata = {}
            provider = _metadata_value(provider_metadata.get("provider"))
            model = _metadata_value(provider_metadata.get("model"))
            run_status = str(metadata.get("run_status", "")).strip() or "unknown"
            status_counts[run_status] += 1
            model_groups[_group_key(provider, model, None)] += 1
            if not isinstance(metadata.get("token_usage"), dict):
                missing_token_usage_count += 1
            artifacts.append(
                {
                    "artifact_type": artifact_type,
                    "item_id": str(metadata.get("item_id", "")).strip(),
                    "run_id": str(metadata.get("run_id", "")).strip(),
                    "run_requested": bool(metadata.get("run_requested", False)),
                    "run_status": run_status,
                    "provider": provider,
                    "model": model,
                    "metadata_path": str(path),
                    "token_usage_available": isinstance(metadata.get("token_usage"), dict)
                    and bool(metadata.get("token_usage", {}).get("available", False)),
                }
            )

    return {
        "artifact_type": artifact_type,
        "artifact_dir": str(artifact_dir.resolve()),
        "artifact_count": len(artifacts),
        "invalid_metadata_count": len(invalid_metadata),
        "invalid_metadata": invalid_metadata,
        "missing_token_usage_count": missing_token_usage_count,
        "status_counts": dict(sorted(status_counts.items())),
        "model_provider_counts": _counter_entries(model_groups),
        "artifacts": artifacts,
    }


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _metadata_value(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _group_key(provider: str | None, model: str | None, reasoning_effort: str | None) -> str:
    return json.dumps(
        {
            "provider": provider,
            "model": model,
            "reasoning_effort": reasoning_effort,
        },
        sort_keys=True,
    )


def _counter_entries(counter: Counter[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key, count in sorted(counter.items()):
        entry = json.loads(key)
        entry["count"] = count
        entries.append(entry)
    return entries


def _stdout_result(command: str, payload: dict[str, Any], output_format: str, markdown: str) -> dict[str, Any]:
    fmt = str(output_format or "json").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {"format": output_format, "supported_formats": ["json", "markdown"]},
        }
    return {
        "command": command,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    codex = payload.get("codex_dispatch", {}) if isinstance(payload.get("codex_dispatch"), dict) else {}
    token_usage = codex.get("token_usage", {}) if isinstance(codex.get("token_usage"), dict) else {}
    advisory = payload.get("local_llm_advisory", {}) if isinstance(payload.get("local_llm_advisory"), dict) else {}
    drafts = payload.get("local_coding_drafts", {}) if isinstance(payload.get("local_coding_drafts"), dict) else {}
    return "\n".join(
        [
            "# Model Usage and Token Accounting Report",
            "",
            f"- ok: {payload.get('ok')}",
            f"- codex_dispatch_runs: {codex.get('run_count', 0)}",
            f"- codex_token_usage_available: {token_usage.get('available_count', 0)}",
            f"- codex_token_usage_unavailable: {token_usage.get('unavailable_count', 0)}",
            f"- codex_total_tokens: {token_usage.get('total_tokens', 0)}",
            f"- local_llm_advisory_artifacts: {advisory.get('artifact_count', 0)}",
            f"- local_coding_draft_artifacts: {drafts.get('artifact_count', 0)}",
            f"- next_safe_action: {payload.get('next_safe_action', '')}",
        ]
    )
