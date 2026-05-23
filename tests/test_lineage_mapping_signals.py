import pytest

from aresforge.operator.lineage_mapping_signals import (
    BLOCKED_STATE,
    READY_STATE,
    SIGNAL_CASE_AMBIGUOUS,
    SIGNAL_CASE_CONFLICTING,
    SIGNAL_CASE_INCOMPLETE,
    SIGNAL_CASE_MISSING,
    SIGNAL_CASE_READY,
    UNKNOWN_STATE,
    WARNING_STATE,
    LineageMappingSignal,
    aggregate_lineage_mapping_signals,
)


def _signal(*, key: str, status: str, signal_case: str, guidance: tuple[str, ...] = ()) -> LineageMappingSignal:
    return LineageMappingSignal(
        signal_key=key,
        source="fixture",
        confidence=1.0,
        status=status,
        signal_case=signal_case,
        parent_issue=381,
        child_issue=382,
        evidence_comment_marker="evidence:ok",
        pr_mapping_marker="pr:ok",
        repair_guidance=guidance,
    )


def test_aggregate_lineage_mapping_signals_ready_state() -> None:
    result = aggregate_lineage_mapping_signals(
        [
            _signal(key="lineage.parent_child", status=READY_STATE, signal_case=SIGNAL_CASE_READY),
            _signal(key="evidence.child_marker", status=READY_STATE, signal_case=SIGNAL_CASE_READY),
            _signal(key="pr.mapping", status=READY_STATE, signal_case=SIGNAL_CASE_READY),
        ]
    )

    payload = result.to_dict()
    assert payload["aggregate_state"] == READY_STATE
    assert payload["closeout_ready"] is True
    assert payload["blocked_reasons"] == []
    assert payload["warning_reasons"] == []


def test_aggregate_lineage_mapping_signals_missing_is_blocked() -> None:
    result = aggregate_lineage_mapping_signals(
        [
            _signal(
                key="lineage.parent_child",
                status=BLOCKED_STATE,
                signal_case=SIGNAL_CASE_MISSING,
                guidance=("Add explicit parent-child links.",),
            )
        ]
    )

    payload = result.to_dict()
    assert payload["aggregate_state"] == BLOCKED_STATE
    assert payload["closeout_ready"] is False
    assert payload["blocked_reasons"] == ["lineage.parent_child:missing"]
    assert payload["repair_guidance"] == ["Add explicit parent-child links."]


def test_aggregate_lineage_mapping_signals_ambiguous_is_warning() -> None:
    result = aggregate_lineage_mapping_signals(
        [
            _signal(
                key="pr.mapping",
                status=WARNING_STATE,
                signal_case=SIGNAL_CASE_AMBIGUOUS,
                guidance=("Clarify one PR per child issue.",),
            )
        ]
    )

    payload = result.to_dict()
    assert payload["aggregate_state"] == WARNING_STATE
    assert payload["closeout_ready"] is False
    assert payload["warning_reasons"] == ["pr.mapping:ambiguous"]


def test_aggregate_lineage_mapping_signals_conflicting_is_blocked() -> None:
    result = aggregate_lineage_mapping_signals(
        [
            _signal(
                key="evidence.child_marker",
                status=BLOCKED_STATE,
                signal_case=SIGNAL_CASE_CONFLICTING,
                guidance=("Remove conflicting evidence markers and keep one canonical marker.",),
            )
        ]
    )

    payload = result.to_dict()
    assert payload["aggregate_state"] == BLOCKED_STATE
    assert payload["blocked_reasons"] == ["evidence.child_marker:conflicting"]


def test_aggregate_lineage_mapping_signals_incomplete_is_warning() -> None:
    result = aggregate_lineage_mapping_signals(
        [
            _signal(
                key="evidence.child_marker",
                status=WARNING_STATE,
                signal_case=SIGNAL_CASE_INCOMPLETE,
                guidance=("Add missing validation and safety lines.",),
            )
        ]
    )

    payload = result.to_dict()
    assert payload["aggregate_state"] == WARNING_STATE
    assert payload["warning_reasons"] == ["evidence.child_marker:incomplete"]


def test_aggregate_lineage_mapping_signals_is_deterministic() -> None:
    first = aggregate_lineage_mapping_signals(
        [
            _signal(key="pr.mapping", status=READY_STATE, signal_case=SIGNAL_CASE_READY),
            _signal(key="lineage.parent_child", status=READY_STATE, signal_case=SIGNAL_CASE_READY),
        ]
    ).to_dict()
    second = aggregate_lineage_mapping_signals(
        [
            _signal(key="lineage.parent_child", status=READY_STATE, signal_case=SIGNAL_CASE_READY),
            _signal(key="pr.mapping", status=READY_STATE, signal_case=SIGNAL_CASE_READY),
        ]
    ).to_dict()
    assert first == second


def test_aggregate_lineage_mapping_signals_empty_input_is_unknown() -> None:
    payload = aggregate_lineage_mapping_signals([]).to_dict()
    assert payload["aggregate_state"] == UNKNOWN_STATE
    assert payload["closeout_ready"] is False
    assert payload["unknown_reasons"] == ["no_preflight_signals_detected"]


def test_lineage_mapping_signal_validates_constraints() -> None:
    with pytest.raises(ValueError):
        LineageMappingSignal(
            signal_key="invalid",
            source="fixture",
            confidence=1.2,
            status=READY_STATE,
            signal_case=SIGNAL_CASE_READY,
        )
