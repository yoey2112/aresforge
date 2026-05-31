import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.source_patch_apply_dry_run import (
    DEFAULT_ITEM_ID,
    dry_run_source_patch_apply,
)


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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m149-controlled-source-patch-apply-plan",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M149 Controlled Source Patch Apply Plan",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m149"],
        source="unit-test",
        notes="Predecessor evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M150 Machine-Gated Source Patch Apply Dry Run",
        description="Dry-run source patch application under machine gates.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m150", "machine-gated"],
        dependencies=["m149-controlled-source-patch-apply-plan"],
        source="unit-test",
        notes="Dry-run only; no patch application.",
    )["ok"] is True


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_patch(tmp_path: Path, text: str) -> Path:
    patch_path = tmp_path / "artifacts" / "manual" / "sample.patch"
    _write(patch_path, text)
    return patch_path


def test_dry_run_source_patch_apply_passes_without_mutating(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    source = tmp_path / "src" / "aresforge" / "operator" / "example.py"
    test_file = tmp_path / "tests" / "test_example.py"
    _write(source, 'VALUE = "old"\n')
    _write(test_file, "def test_old():\n    assert True\n")
    patch_path = _write_patch(
        tmp_path,
        """diff --git a/src/aresforge/operator/example.py b/src/aresforge/operator/example.py
--- a/src/aresforge/operator/example.py
+++ b/src/aresforge/operator/example.py
@@ -1 +1,2 @@
 VALUE = "old"
+CONTROLLED_PATCH_DRY_RUN = True
diff --git a/tests/test_example.py b/tests/test_example.py
--- a/tests/test_example.py
+++ b/tests/test_example.py
@@ -1,2 +1,3 @@
 def test_old():
+    assert "dry-run"
     assert True
""",
    )

    payload = dry_run_source_patch_apply(config, patch_path=patch_path)["payload"]

    assert payload["record_type"] == "source_patch_apply_dry_run_v1"
    assert payload["artifact_type"] == "source_patch_apply_dry_run_v1"
    assert payload["status"] == "dry_run_passed"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["patch_application_dry_run_performed"] is True
    assert payload["dry_run_apply_check"]["passed"] is True
    assert payload["patch_application_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["validation_command_execution_performed"] is False
    assert payload["local_only"] is True
    assert source.read_text(encoding="utf-8") == 'VALUE = "old"\n'
    assert test_file.read_text(encoding="utf-8") == "def test_old():\n    assert True\n"


def test_dry_run_source_patch_apply_reports_failed_apply_check(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _write(tmp_path / "src" / "aresforge" / "operator" / "example.py", 'VALUE = "different"\n')
    patch_path = _write_patch(
        tmp_path,
        """diff --git a/src/aresforge/operator/example.py b/src/aresforge/operator/example.py
--- a/src/aresforge/operator/example.py
+++ b/src/aresforge/operator/example.py
@@ -1 +1,2 @@
 VALUE = "old"
+CONTROLLED_PATCH_DRY_RUN = True
""",
    )

    result = dry_run_source_patch_apply(config, patch_path=patch_path)
    payload = result["payload"]

    assert result["ok"] is False
    assert payload["status"] == "dry_run_failed"
    assert payload["blocked"] is True
    assert payload["patch_application_dry_run_performed"] is True
    assert payload["dry_run_apply_check"]["passed"] is False
    assert payload["patch_application_performed"] is False


def test_dry_run_source_patch_apply_blocks_workflow_patch_before_check(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    patch_path = _write_patch(
        tmp_path,
        """diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -1 +1,2 @@
 name: ci
+on: push
""",
    )

    payload = dry_run_source_patch_apply(config, patch_path=patch_path)["payload"]

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["patch_application_dry_run_performed"] is False
    assert payload["dry_run_apply_check"]["performed"] is False
    assert "workflow_mutation" in payload["hard_apply_blockers"]
    assert payload["patch_application_performed"] is False


def test_dry_run_source_patch_apply_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _write(tmp_path / "src" / "aresforge" / "example.py", "value = 1\n")
    patch_path = _write_patch(
        tmp_path,
        """diff --git a/src/aresforge/example.py b/src/aresforge/example.py
--- a/src/aresforge/example.py
+++ b/src/aresforge/example.py
@@ -1 +1,2 @@
 value = 1
+value = 2
""",
    )
    output = tmp_path / ".aresforge" / "source_patch_apply_dry_runs" / "dry-run.json"

    result = dry_run_source_patch_apply(config, patch_path=patch_path, output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "source_patch_apply_dry_run_v1"
    assert str(output) in written["artifacts_created"]
