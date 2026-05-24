from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.closeout_readiness_by_construction import check_closeout_readiness_by_construction
from aresforge.operator.evidence_completeness_checker import check_milestone_evidence_readiness
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.parent_closeout_evidence_bundle import generate_parent_closeout_evidence_bundle
from aresforge.operator.parent_closeout_readiness import inspect_parent_closeout_readiness


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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def test_offline_state_example_fixture_supports_full_offline_closeout_flow(tmp_path: Path) -> None:
    config = _config(tmp_path)
    fixture = Path(__file__).parent / "fixtures" / "offline_state" / "parent_closeout_ready.json"

    milestone = inspect_milestone_state(config, parent_issue=421, state_file=fixture)
    assert milestone["ok"] is True
    assert milestone["inspection_mode"] == "local_state_file"

    evidence = check_milestone_evidence_readiness(config, parent_issue=421, state_file=fixture)
    assert evidence["ok"] is True
    assert evidence["inspection_mode"] == "local_state_file"

    readiness = inspect_parent_closeout_readiness(config, parent_issue=421, state_file=fixture)
    assert readiness["ok"] is True
    assert readiness["inspection_mode"] == "local_state_file"
    assert readiness["closeout_readiness"]["parent_closeout_ready"] is True

    parent_bundle = generate_parent_closeout_evidence_bundle(config, parent_issue=421, state_file=fixture)
    assert parent_bundle["ok"] is True
    assert parent_bundle["inspection_mode"] == "local_state_file"
    assert parent_bundle["canonical_marker_completeness"]["marker_complete"] is True

    by_construction = check_closeout_readiness_by_construction(config, parent_issue=421, state_file=fixture)
    assert by_construction["ok"] is True
    assert by_construction["inspection_mode"] == "local_state_file"
    assert by_construction["readiness_by_construction"]["ready"] is True
