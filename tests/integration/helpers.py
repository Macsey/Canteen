from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable

from simulation import Simulation


ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "reports" / "artifacts"


def poisson_sequence(values: Iterable[int]) -> Callable[[float], int]:
    """Return deterministic poisson samples, repeating 0 after values end."""
    iterator = iter(values)

    def _sample(_arrival_lambda: float) -> int:
        try:
            return int(next(iterator))
        except StopIteration:
            return 0

    return _sample


def total_capacity(sim: Simulation) -> int:
    return sim.table.rows * sim.table.cols * sim.table.capacity_per_unit


def active_student_count(sim: Simulation) -> int:
    window_count = sum(window.queue_length() for window in sim.windows)
    return (
        window_count
        + len(sim.waiting_for_seat)
        + len(sim.eating_students)
        + sim.total_finished
    )


def final_state(sim: Simulation) -> dict[str, Any]:
    return {
        "current_time": sim.current_time,
        "total_arrived": sim.total_arrived,
        "total_finished": sim.total_finished,
        "waiting_for_seat_count": len(sim.waiting_for_seat),
        "eating_count": len(sim.eating_students),
        "available_seats": sim.table.available_count(),
        "window_queue_lengths": [window.queue_length() for window in sim.windows],
        "active_student_count": active_student_count(sim),
    }


def write_artifact(
    file_name: str,
    case_name: str,
    input_config: dict[str, Any],
    records: list[dict[str, Any]],
    state: dict[str, Any],
    key_observations: dict[str, Any],
    pass_or_fail: bool,
    failure_reason: str = "",
) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = {
        "case_name": case_name,
        "input_config": input_config,
        "records": records,
        "final_state": state,
        "key_observations": key_observations,
        "pass_or_fail": bool(pass_or_fail),
        "failure_reason": failure_reason,
    }
    path = ARTIFACT_DIR / file_name
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

