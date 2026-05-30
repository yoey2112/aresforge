import json
from pathlib import Path
from urllib import error, request

from aresforge.config import AppConfig
from aresforge.operator.local_llm_advisory import build_local_llm_advisory_run_artifact


def _config(tmp_path: Path) -> AppConfig:
    artifact_root = tmp_path / "artifacts"
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=artifact_root,
        prompts_dir=artifact_root / "prompts" / "generated",
        evidence_dir=artifact_root / "evidence" / "generated",
        codex_handoffs_dir=artifact_root / "codex_handoffs" / "generated",
        github_owner="local",
        github_repo="aresforge",
    )


def _write_queue(tmp_path: Path) -> None:
    queue_path = tmp_path / ".aresforge" / "queue" / "work_items.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-05-30T00:00:00+00:00",
                "work_items": [
                    {
                        "item_id": "m85-test",
                        "project_id": "aresforge",
                        "repo_id": "aresforge-main",
                        "title": "M85 test item",
                        "description": "Prepare local LLM advisory artifacts.",
                        "status": "proposed",
                        "priority": "high",
                        "item_type": "feature",
                        "tags": ["local-llm"],
                        "dependencies": [],
                        "blocked_by": [],
                        "notes": "Keep output advisory and non-mutating.",
                        "routing_metadata": {},
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_local_llm_advisory_artifact_generates_prompt_without_provider_call(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(tmp_path)

    payload = build_local_llm_advisory_run_artifact(
        config,
        item_id="m85-test",
        run_id="m85-dry-run",
    )

    assert payload["ok"] is True
    assert payload["run_requested"] is False
    assert payload["run_status"] == "prepared_not_run"
    assert payload["response_path"] == ""
    assert payload["safety_boundary"]["provider_invocation_allowed_from_this_command"] is False
    assert payload["safety_boundary"]["repo_mutation_allowed"] is False
    assert payload["safety_boundary"]["automatic_next_item_execution_allowed"] is False
    prompt_path = Path(payload["prompt_path"])
    assert prompt_path.exists()
    assert "Required Response JSON Fields" in prompt_path.read_text(encoding="utf-8")


def test_local_llm_advisory_run_writes_response_metadata_with_mocked_ollama(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(tmp_path)
    seen: list[tuple[str, str]] = []

    def fake_urlopen(req: request.Request, timeout: int) -> _FakeResponse:
        seen.append((req.full_url, req.get_method()))
        if req.full_url.endswith("/api/tags"):
            return _FakeResponse({"models": [{"name": "qwen2.5:32b", "model": "qwen2.5:32b"}]})
        assert req.full_url.endswith("/api/generate")
        return _FakeResponse({"response": "{\"summary\":\"advisory only\"}"})

    payload = build_local_llm_advisory_run_artifact(
        config,
        item_id="m85-test",
        run=True,
        run_id="m85-run",
        urlopen_fn=fake_urlopen,
    )

    assert payload["ok"] is True
    assert payload["run_requested"] is True
    assert payload["run_status"] == "completed_advisory"
    assert ("http://127.0.0.1:11434/api/tags", "GET") in seen
    assert ("http://127.0.0.1:11434/api/generate", "POST") in seen
    assert Path(payload["response_path"]).read_text(encoding="utf-8") == "{\"summary\":\"advisory only\"}"
    metadata = json.loads(Path(payload["metadata_path"]).read_text(encoding="utf-8"))
    assert metadata["safety_boundary"]["repo_mutation_allowed"] is False
    assert metadata["safety_boundary"]["queue_completion_allowed"] is False


def test_local_llm_advisory_run_handles_unavailable_provider_without_generation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(tmp_path)
    seen: list[str] = []

    def fake_urlopen(req: request.Request, timeout: int) -> _FakeResponse:
        seen.append(req.full_url)
        raise error.URLError("connection refused")

    payload = build_local_llm_advisory_run_artifact(
        config,
        item_id="m85-test",
        run=True,
        run_id="m85-unavailable",
        urlopen_fn=fake_urlopen,
    )

    assert payload["ok"] is True
    assert payload["run_status"] == "unavailable"
    assert payload["response_path"] == ""
    assert seen == ["http://127.0.0.1:11434/api/tags"]
    assert payload["safety_boundary"]["repo_mutation_allowed"] is False
