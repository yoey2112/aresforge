from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoutePlan:
    work_item_id: str | None
    queue_id: str
    agent_id: str
    model_id: str
    prompt_package: str | None
    route_status: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "work_item_id": self.work_item_id,
            "queue_id": self.queue_id,
            "agent_id": self.agent_id,
            "model_id": self.model_id,
            "prompt_package": self.prompt_package,
            "route_status": self.route_status,
        }


def build_route_plan(
    *,
    work_item_id: str | None,
    queue_id: str,
    agent_id: str,
    model_id: str,
    prompt_package: str | None,
    route_status: str,
) -> RoutePlan:
    return RoutePlan(
        work_item_id=work_item_id,
        queue_id=queue_id,
        agent_id=agent_id,
        model_id=model_id,
        prompt_package=prompt_package,
        route_status=route_status,
    )
