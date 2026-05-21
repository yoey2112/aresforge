import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.agent_queue_planning import plan_agent_queue


def make_config(tmp_path: Path) -> AppConfig:
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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def test_plan_agent_queue_from_local_issues_file(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    issues_path = tmp_path / "issues.json"
    issues_path.write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "number": 165,
                        "title": "Contract issue",
                        "url": "https://example.test/165",
                        "labels": ["aresforge-ready", "aresforge-automerge"],
                    },
                    {
                        "number": 166,
                        "title": "Needs attention",
                        "labels": ["aresforge-ready", "aresforge-needs-docs"],
                    },
                    {
                        "number": 169,
                        "title": "Blocked",
                        "labels": ["aresforge-blocked"],
                    },
                    {"number": 39, "title": "Protected"},
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = plan_agent_queue(config, issues_file=str(issues_path))

    assert payload["ok"] is True
    assert payload["input_mode"] == "issues_file"
    assert payload["queue_contract_version"] == "m7-governance-aware-intake"
    assert payload["excluded_issues"] == [{"number": 39, "reason": "protected_issue"}]
    assert [item["issue_number"] for item in payload["queue_items"]] == [165, 166, 169]
    assert payload["queue_items"][0]["readiness"] == "ready"
    assert payload["queue_items"][0]["planning_state"] == "ready"
    assert payload["queue_items"][1]["readiness"] == "attention_needed"
    assert payload["queue_items"][1]["planning_state"] == "planned"
    assert payload["queue_items"][2]["readiness"] == "blocked"
    assert payload["queue_items"][2]["planning_state"] == "blocked"
    assert payload["persisted_planning_state_design"]["mutation_posture"] == "read_only_design_only"
    assert payload["persisted_planning_state_design"]["states"][0] == "queued"
    assert json.loads(json.dumps(payload)) == payload
