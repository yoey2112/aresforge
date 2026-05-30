# Sample Codex Result For M112 Smoke

**Files Changed**
- src/aresforge/operator/dispatch_result_evidence_parser.py
- src/aresforge/cli.py
- tests/test_dispatch_result_evidence_parser.py
- tests/test_cli.py

**What Changed**
- Added `parse-dispatch-result-evidence` for local-only parsing of human-pasted Codex result text.
- The evidence record keeps `human_review_required=true`, `local_only=true`, and `execution_allowed=false`.

**Tests Run And Results**
- python -m pytest tests/test_cli.py -> passed
- python -m pytest tests/test_dispatch_result_evidence_parser.py -> passed
- git diff --check -> passed with CRLF warnings only

**Smoke Checks Run And Results**
- python -m aresforge parse-dispatch-result-evidence --item-id m112-dispatch-result-evidence-parser --result-path artifacts/manual/sample-codex-result.md --format json -> passed

**Warnings Or Blockers**
- No blockers.

**Commit Hash**
- abc1234
