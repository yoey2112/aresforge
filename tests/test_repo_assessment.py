import json
from pathlib import Path

from aresforge import cli
from aresforge.config import AppConfig
from aresforge.operator.repo_assessment import AssessmentOptions, assess_repository


def _make_config(repo_root: Path) -> AppConfig:
    return AppConfig(
        repo_root=repo_root,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=repo_root / "artifacts",
        prompts_dir=repo_root / "artifacts" / "prompts" / "generated",
        evidence_dir=repo_root / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=repo_root / "artifacts" / "codex_handoffs" / "generated",
        github_owner="example",
        github_repo="aresforge",
    )


def _write(path: Path, body: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(body, bytes):
        path.write_bytes(body)
    else:
        path.write_text(body, encoding="utf-8")


def test_assessment_inventories_files_and_parses_python_and_outputs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo / "src/aresforge/cli.py", 'from aresforge.operator.repo_assessment import assess_repository\n')
    _write(repo / "src/aresforge/operator/sample.py", "import os\nfrom pathlib import Path\n\nclass Example:\n    pass\n\ndef feature():\n    return True\n")
    _write(repo / "src/aresforge/hub/api.py", '@app.get("/api/health")\ndef health():\n    return {"ok": True}\n')
    _write(repo / "tests/test_sample.py", "from aresforge.operator.sample import feature\n")
    _write(repo / "docs/architecture/claims.md", "GitHub Actions automation runner and autonomous execution")
    _write(repo / "artifacts/out.json", "{}")
    _write(repo / "__pycache__/ignored.pyc", b"\x00\x01")

    config = _make_config(repo)
    out = repo / "docs" / "audit"
    result = assess_repository(
        config,
        options=AssessmentOptions(
            repo_path=repo,
            output_path=out,
            format="both",
            include_tests=True,
            include_docs=True,
            force=False,
        ),
    )

    assert result["ok"] is True
    assert (out / "REPO_FILE_MAP.json").exists()
    assert (out / "REPO_FILE_MAP.md").exists()
    assert (out / "ARCHITECTURE_DOMAIN_MAP.md").exists()
    assert (out / "GAP_REGISTER_DRAFT.md").exists()
    assert (out / "ASSESSMENT_SUMMARY.md").exists()

    payload = json.loads((out / "REPO_FILE_MAP.json").read_text(encoding="utf-8"))
    paths = {item["path"] for item in payload["files"]}
    assert "src/aresforge/operator/sample.py" in paths
    assert "tests/test_sample.py" in paths
    assert "__pycache__/ignored.pyc" not in paths

    sample = next(item for item in payload["files"] if item["path"] == "src/aresforge/operator/sample.py")
    assert "os" in sample["imports"]
    assert "Example" in sample["classes"]
    assert "feature" in sample["functions"]


def test_force_required_for_overwrite(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo / "src/aresforge/cli.py", "print('ok')\n")
    out = repo / "docs" / "audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "REPO_FILE_MAP.json").write_text("{}", encoding="utf-8")

    config = _make_config(repo)
    blocked = assess_repository(
        config,
        options=AssessmentOptions(repo_path=repo, output_path=out, format="json", include_tests=True, include_docs=True, force=False),
    )
    assert blocked["ok"] is False
    assert blocked["error"] == "output_exists"

    allowed = assess_repository(
        config,
        options=AssessmentOptions(repo_path=repo, output_path=out, format="json", include_tests=True, include_docs=True, force=True),
    )
    assert allowed["ok"] is True


def test_plan_only_and_docs_claim_gaps(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo / "src/aresforge/cli.py", "print('ok')\n")
    _write(repo / "src/aresforge/operator/plan_only.py", "# plan-only\n# no execution\n")
    _write(repo / "docs/architecture/runtime.md", "This uses GitHub Actions automation runner")

    config = _make_config(repo)
    out = repo / "docs" / "audit"
    result = assess_repository(
        config,
        options=AssessmentOptions(repo_path=repo, output_path=out, format="json", include_tests=True, include_docs=True, force=True),
    )
    assert result["ok"] is True

    payload = json.loads((out / "REPO_FILE_MAP.json").read_text(encoding="utf-8"))
    plan_file = next(item for item in payload["files"] if item["path"] == "src/aresforge/operator/plan_only.py")
    assert plan_file["status_classification"] == "plan_only"

    gap_ids = {gap["id"] for gap in payload["gaps"]}
    assert "no_github_workflows" in gap_ids
    assert "docs_claim_runtime_gap" in gap_ids


def test_assess_repo_cli_wired_and_returns_ok(monkeypatch, capsys, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo / "src/aresforge/cli.py", "print('ok')\n")
    config = _make_config(repo)

    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    exit_code = cli.main([
        "assess-repo",
        "--repo-path",
        str(repo),
        "--output",
        "docs/audit",
        "--format",
        "json",
        "--force",
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert (repo / "docs" / "audit" / "REPO_FILE_MAP.json").exists()
