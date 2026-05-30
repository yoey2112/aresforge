import json
import subprocess
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.docs_only_patch_apply import apply_docs_only_patch
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue


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


def _run(repo_root: Path, *args: str) -> None:
    subprocess.run(args, cwd=repo_root, check=True, capture_output=True, text=True)


def _seed_repo(config: AppConfig) -> None:
    docs_target = config.repo_root / "docs" / "operator" / "LOCAL_OPERATOR_USAGE.md"
    docs_target.parent.mkdir(parents=True, exist_ok=True)
    docs_target.write_text("old docs text\n", encoding="utf-8")
    source_target = config.repo_root / "src" / "aresforge" / "example.py"
    source_target.parent.mkdir(parents=True, exist_ok=True)
    source_target.write_text("old source text\n", encoding="utf-8")
    test_target = config.repo_root / "tests" / "test_example.py"
    test_target.parent.mkdir(parents=True, exist_ok=True)
    test_target.write_text("old test text\n", encoding="utf-8")

    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m132-auto-completion-for-safe-queue-items",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M132 dependency",
        status="done",
        priority="high",
        item_type="feature",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m133-docs-only",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M133 docs-only patch apply",
        status="in_progress",
        priority="high",
        item_type="documentation",
        tags=["milestone:m133", "local-only"],
        dependencies=["m132-auto-completion-for-safe-queue-items"],
        completion_requires=["tests_run", "smoke_checks"],
        evidence_required=["docs_only_patch_apply"],
        notes="Validation evidence present.",
    )["ok"] is True
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in queue["work_items"]:
        if item["item_id"] == "m133-docs-only":
            item["tests_run"] = ["python -m pytest -> passed"]
            item["validation_summary"] = "Validation commands are runnable and reported as passed."
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")

    _run(config.repo_root, "git", "init")
    _run(config.repo_root, "git", "config", "user.email", "tests@example.com")
    _run(config.repo_root, "git", "config", "user.name", "AresForge Tests")
    _run(config.repo_root, "git", "add", ".")
    _run(config.repo_root, "git", "commit", "-m", "seed docs-only patch apply fixture")


def _patch(config: AppConfig, target: str, *, new_text: str = "new docs text", mode: str = "") -> Path:
    path = config.repo_root / "artifacts" / "manual" / f"{target.replace('/', '_')}.patch"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"diff --git a/{target} b/{target}",
    ]
    if mode:
        lines.append(mode)
    lines.extend(
        [
            f"--- a/{target}",
            f"+++ b/{target}",
            "@@ -1 +1 @@",
            "-old docs text" if target.startswith("docs/") else "-old source text" if target.startswith("src/") else "-old test text",
            f"+{new_text}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_docs_only_patch_dry_run_does_not_apply(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_repo(config)
    patch = _patch(config, "docs/operator/LOCAL_OPERATOR_USAGE.md")

    result = apply_docs_only_patch(config, item_id="m133-docs-only", patch_path=patch, dry_run=True)
    payload = json.loads(result["stdout"])

    assert result["ok"] is True
    assert payload["action_type"] == "docs_only_patch_apply"
    assert payload["dry_run"] is True
    assert payload["applied"] is False
    assert payload["patch_application_performed"] is False
    assert payload["machine_gates_checked"] is True
    assert payload["machine_gates_passed"] is True
    assert (tmp_path / "docs" / "operator" / "LOCAL_OPERATOR_USAGE.md").read_text(encoding="utf-8") == "old docs text\n"


def test_docs_only_patch_applies_and_logs_transaction(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_repo(config)
    patch = _patch(config, "docs/operator/LOCAL_OPERATOR_USAGE.md")

    result = apply_docs_only_patch(config, item_id="m133-docs-only", patch_path=patch)
    payload = json.loads(result["stdout"])
    log = json.loads((tmp_path / ".aresforge" / "queue" / "transaction_log.json").read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert payload["applied"] is True
    assert payload["patch_application_performed"] is True
    assert payload["source_code_changed"] is False
    assert payload["tests_changed"] is False
    assert payload["changed_files"] == ["docs/operator/LOCAL_OPERATOR_USAGE.md"]
    assert payload["transaction_log_entry"]["mutation_type"] == "docs_only_patch_apply"
    assert log["transactions"][-1]["mutation_type"] == "docs_only_patch_apply"
    assert (tmp_path / "docs" / "operator" / "LOCAL_OPERATOR_USAGE.md").read_text(encoding="utf-8") == "new docs text\n"


def test_docs_only_patch_blocks_src_changes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_repo(config)
    patch = _patch(config, "src/aresforge/example.py")

    result = apply_docs_only_patch(config, item_id="m133-docs-only", patch_path=patch)
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert payload["source_code_changed"] is False
    assert any("Source code path is blocked" in reason for reason in payload["blocked_reasons"])


def test_docs_only_patch_blocks_tests_changes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_repo(config)
    patch = _patch(config, "tests/test_example.py")

    result = apply_docs_only_patch(config, item_id="m133-docs-only", patch_path=patch)
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert payload["tests_changed"] is False
    assert any("Test path is blocked" in reason for reason in payload["blocked_reasons"])


def test_docs_only_patch_blocks_binary_and_non_doc_files(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_repo(config)
    patch = config.repo_root / "artifacts" / "manual" / "binary.patch"
    patch.parent.mkdir(parents=True, exist_ok=True)
    patch.write_text(
        "\n".join(
            [
                "diff --git a/docs/image.png b/docs/image.png",
                "new file mode 100644",
                "GIT binary patch",
                "literal 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = apply_docs_only_patch(config, item_id="m133-docs-only", patch_path=patch, dry_run=True)
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert payload["binary_patch_detected"] is True
    assert any("Binary patch content is not allowed" in reason for reason in payload["blocked_reasons"])
    assert any("Path is outside the docs-only Markdown allowlist" in reason for reason in payload["blocked_reasons"])


def test_docs_only_patch_blocks_hidden_executable_changes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_repo(config)
    patch = _patch(config, "docs/operator/LOCAL_OPERATOR_USAGE.md", mode="old mode 100644\nnew mode 100755")

    result = apply_docs_only_patch(config, item_id="m133-docs-only", patch_path=patch, dry_run=True)
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert payload["hidden_executable_changes_detected"] is True
    assert any("hidden executable" in reason for reason in payload["blocked_reasons"])
