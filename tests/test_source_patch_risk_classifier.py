import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.source_patch_risk_classifier import (
    DEFAULT_ITEM_ID,
    analyze_source_patch,
    classify_source_patch_risk,
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
        item_id="m147-orchestrator-resume-from-failure",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M147 Orchestrator Resume-from-Failure",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m147"],
        source="unit-test",
        notes="Predecessor evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M148 Safe Source Patch Detection and Risk Classifier",
        description="Classify source patches without applying them.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m148", "machine-gated"],
        dependencies=["m147-orchestrator-resume-from-failure"],
        source="unit-test",
        notes="Read-only patch classification only.",
    )["ok"] is True


def _write_patch(tmp_path: Path, text: str) -> Path:
    patch_path = tmp_path / "artifacts" / "manual" / "sample.patch"
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(text, encoding="utf-8")
    return patch_path


def test_classify_source_patch_reports_source_and_tests_risk(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    patch_path = _write_patch(
        tmp_path,
        """diff --git a/src/aresforge/operator/example.py b/src/aresforge/operator/example.py
--- a/src/aresforge/operator/example.py
+++ b/src/aresforge/operator/example.py
@@ -1 +1,2 @@
 VALUE = "old"
+SAFE_SOURCE_PATCH_CLASSIFIER = True
diff --git a/tests/test_example.py b/tests/test_example.py
--- a/tests/test_example.py
+++ b/tests/test_example.py
@@ -1 +1,2 @@
 def test_old():
+    assert True
""",
    )

    payload = classify_source_patch_risk(config, patch_path=patch_path)["payload"]

    assert payload["record_type"] == "source_patch_risk_classification_v1"
    assert payload["artifact_type"] == "source_patch_risk_classification_v1"
    assert payload["status"] == "classified"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["touched_files"] == [
        "src/aresforge/operator/example.py",
        "tests/test_example.py",
    ]
    assert payload["source_code_touched"] is True
    assert payload["tests_touched"] is True
    assert payload["risk_level"] == "high"
    assert payload["mutation_type"] == "mixed_change"
    assert payload["patch_application_allowed_by_classifier"] is False
    assert payload["test_requirements"]["required_before_apply_or_completion"] is True
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True


def test_source_patch_analysis_detects_workflow_and_binary_blocked_operations() -> None:
    analysis = analyze_source_patch(
        """diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -1 +1,2 @@
 name: ci
+on: push
diff --git a/assets/icon.png b/assets/icon.png
GIT binary patch
literal 0
"""
    )

    detected = {
        entry["operation_id"]
        for entry in analysis["blocked_operations"]
        if entry["detected"]
    }
    assert analysis["risk_level"] == "critical"
    assert "workflow_mutation" in detected
    assert "binary_patch_application" in detected


def test_classify_source_patch_blocks_missing_patch_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = classify_source_patch_risk(config, patch_path=tmp_path / "missing.patch")
    payload = result["payload"]

    assert result["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert any("Patch file is missing" in reason for reason in payload["blocked_reasons"])
    assert payload["patch_application_performed"] is False


def test_classify_source_patch_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
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
    output = tmp_path / ".aresforge" / "source_patch_risk" / "classification.json"

    result = classify_source_patch_risk(config, patch_path=patch_path, output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "source_patch_risk_classification_v1"
    assert str(output) in written["artifacts_created"]
