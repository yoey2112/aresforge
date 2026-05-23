from __future__ import annotations

from dataclasses import dataclass
from typing import Any


READY_STATE = "ready"
BLOCKED_STATE = "blocked"
WARNING_STATE = "warning"
UNKNOWN_STATE = "unknown"

SIGNAL_CASE_READY = "ready"
SIGNAL_CASE_MISSING = "missing"
SIGNAL_CASE_AMBIGUOUS = "ambiguous"
SIGNAL_CASE_CONFLICTING = "conflicting"
SIGNAL_CASE_INCOMPLETE = "incomplete"

ALLOWED_AGGREGATE_STATES = {
    READY_STATE,
    BLOCKED_STATE,
    WARNING_STATE,
    UNKNOWN_STATE,
}
ALLOWED_SIGNAL_CASES = {
    SIGNAL_CASE_READY,
    SIGNAL_CASE_MISSING,
    SIGNAL_CASE_AMBIGUOUS,
    SIGNAL_CASE_CONFLICTING,
    SIGNAL_CASE_INCOMPLETE,
}


@dataclass(frozen=True)
class LineageMappingSignal:
    signal_key: str
    source: str
    confidence: float
    status: str
    signal_case: str
    parent_issue: int | None = None
    child_issue: int | None = None
    evidence_comment_marker: str | None = None
    pr_mapping_marker: str | None = None
    repair_guidance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_AGGREGATE_STATES:
            raise ValueError(f"Unsupported signal status: {self.status}")
        if self.signal_case not in ALLOWED_SIGNAL_CASES:
            raise ValueError(f"Unsupported signal case: {self.signal_case}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("signal confidence must be within [0.0, 1.0]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_key": self.signal_key,
            "source": self.source,
            "confidence": self.confidence,
            "status": self.status,
            "signal_case": self.signal_case,
            "parent_issue": self.parent_issue,
            "child_issue": self.child_issue,
            "evidence_comment_marker": self.evidence_comment_marker,
            "pr_mapping_marker": self.pr_mapping_marker,
            "repair_guidance": sorted(set(item for item in self.repair_guidance if item)),
        }


@dataclass(frozen=True)
class LineageMappingAggregateResult:
    aggregate_state: str
    closeout_ready: bool
    signals: tuple[LineageMappingSignal, ...]
    blocked_reasons: tuple[str, ...]
    warning_reasons: tuple[str, ...]
    unknown_reasons: tuple[str, ...]
    repair_guidance: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        ordered_signals = sorted(
            self.signals,
            key=lambda signal: (
                signal.parent_issue if signal.parent_issue is not None else -1,
                signal.child_issue if signal.child_issue is not None else -1,
                signal.signal_key,
                signal.source,
            ),
        )
        return {
            "aggregate_state": self.aggregate_state,
            "closeout_ready": self.closeout_ready,
            "signals": [signal.to_dict() for signal in ordered_signals],
            "blocked_reasons": list(self.blocked_reasons),
            "warning_reasons": list(self.warning_reasons),
            "unknown_reasons": list(self.unknown_reasons),
            "repair_guidance": list(self.repair_guidance),
        }


def aggregate_lineage_mapping_signals(signals: list[LineageMappingSignal]) -> LineageMappingAggregateResult:
    ordered_signals = tuple(
        sorted(
            signals,
            key=lambda signal: (
                signal.parent_issue if signal.parent_issue is not None else -1,
                signal.child_issue if signal.child_issue is not None else -1,
                signal.signal_key,
                signal.source,
            ),
        )
    )

    if not ordered_signals:
        return LineageMappingAggregateResult(
            aggregate_state=UNKNOWN_STATE,
            closeout_ready=False,
            signals=ordered_signals,
            blocked_reasons=("no_preflight_signals_detected",),
            warning_reasons=(),
            unknown_reasons=("no_preflight_signals_detected",),
            repair_guidance=("Collect parent-child lineage, evidence marker, and PR mapping signals.",),
        )

    blocked_reasons: list[str] = []
    warning_reasons: list[str] = []
    unknown_reasons: list[str] = []
    guidance: list[str] = []

    for signal in ordered_signals:
        if signal.signal_case in {SIGNAL_CASE_MISSING, SIGNAL_CASE_CONFLICTING} or signal.status == BLOCKED_STATE:
            blocked_reasons.append(f"{signal.signal_key}:{signal.signal_case}")
        elif signal.signal_case in {SIGNAL_CASE_AMBIGUOUS, SIGNAL_CASE_INCOMPLETE} or signal.status == WARNING_STATE:
            warning_reasons.append(f"{signal.signal_key}:{signal.signal_case}")
        elif signal.status == UNKNOWN_STATE:
            unknown_reasons.append(f"{signal.signal_key}:{signal.signal_case}")
        guidance.extend(signal.repair_guidance)

    blocked_reasons = sorted(set(blocked_reasons))
    warning_reasons = sorted(set(warning_reasons))
    unknown_reasons = sorted(set(unknown_reasons))
    repair_guidance = tuple(sorted(set(item for item in guidance if item)))

    if blocked_reasons:
        aggregate_state = BLOCKED_STATE
    elif warning_reasons:
        aggregate_state = WARNING_STATE
    elif all(signal.status == READY_STATE and signal.signal_case == SIGNAL_CASE_READY for signal in ordered_signals):
        aggregate_state = READY_STATE
    else:
        aggregate_state = UNKNOWN_STATE

    return LineageMappingAggregateResult(
        aggregate_state=aggregate_state,
        closeout_ready=aggregate_state == READY_STATE,
        signals=ordered_signals,
        blocked_reasons=tuple(blocked_reasons),
        warning_reasons=tuple(warning_reasons),
        unknown_reasons=tuple(unknown_reasons),
        repair_guidance=repair_guidance,
    )
