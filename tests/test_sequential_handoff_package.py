import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import sequential_handoff_package as shp


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


def test_generate_sequential_handoff_package(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)

    def fake_issue(_config, issue_number):
        if issue_number == 309:
            return {"ok": True, "issue": {"number": 309, "title": "Parent", "state": "OPEN", "url": "u", "body": "- [ ] thing (#310)\n- [ ] thing (#314)"}}
        return {
            "ok": True,
            "issue": {
                "number": issue_number,
                "title": f"Issue {issue_number}",
                "state": "OPEN" if issue_number == 314 else "CLOSED",
                "merged_pr_evidence": [{"url": "https://github.com/yoey2112/aresforge/pull/1", "merged_at": "abc"}],
                "comments": [{"url": "https://github.com/yoey2112/aresforge/issues/1#issuecomment-1", "body": "PR\nhttps://github.com/yoey2112/aresforge/pull/1"}],
            },
        }

    monkeypatch.setattr(shp, "fetch_issue_details", fake_issue)
    monkeypatch.setattr(shp, "inspect_milestone_dashboard", lambda _config, parent_issue: {"ok": True, "dashboard": {"parent_should_remain_open": True}, "warnings": []})
    payload = shp.generate_sequential_handoff_package(cfg, parent_issue=309, write_package=False)
    assert payload["ok"] is True
    assert payload["package"]["next_child_recommendation"] == 314
    assert len(payload["package"]["children"]) == 2


def test_generate_sequential_handoff_package_write(monkeypatch, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    monkeypatch.setattr(
        shp,
        "fetch_issue_details",
        lambda _config, issue_number: {
            "ok": True,
            "issue": {
                "number": issue_number,
                "title": "x",
                "state": "OPEN",
                "url": "u",
                "body": "- [ ] child (#314)" if issue_number == 309 else "",
                "merged_pr_evidence": [],
                "comments": [],
            },
        },
    )
    monkeypatch.setattr(shp, "inspect_milestone_dashboard", lambda _config, parent_issue: {"ok": True, "dashboard": {}, "warnings": []})
    payload = shp.generate_sequential_handoff_package(cfg, parent_issue=309, write_package=True)
    assert payload["ok"] is True
    assert payload["read_only"] is False
    artifact = payload["artifact"]
    assert Path(artifact["markdown_path"]).exists()
    saved = json.loads(Path(artifact["json_path"]).read_text(encoding="utf-8"))
    assert saved["parent_issue"]["number"] == 309
