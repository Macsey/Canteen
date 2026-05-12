from __future__ import annotations

import csv

import numpy as np

from logger import DataLogger
from simulation import Simulation

from .helpers import (
    ARTIFACT_DIR,
    active_student_count,
    final_state,
    poisson_sequence,
    total_capacity,
    write_artifact,
)


def test_system_normal_dining_flow(monkeypatch):
    # Arrange
    config = {
        "simulation_time": 8,
        "window_count": 1,
        "table_rows": 1,
        "table_cols": 1,
        "table_capacity_per_unit": 2,
        "avg_service_time": 1,
        "std_service_time": 0,
        "avg_eating_time": 2,
        "std_eating_time": 0,
    }
    sim = Simulation(**config)
    monkeypatch.setattr(np.random, "poisson", poisson_sequence([1, 0, 0, 0, 0, 0, 0, 0]))
    monkeypatch.setattr(sim, "_sample_service_time", lambda: 1)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 2)

    # Act
    records = list(sim.iter_steps())
    state = final_state(sim)
    passed = (
        sim.total_arrived >= 1
        and sim.total_finished >= 1
        and len(records) == config["simulation_time"]
        and sim.table.available_count() == total_capacity(sim)
    )
    write_artifact(
        "normal_flow_case.json",
        "正常低流量就餐闭环",
        config,
        records,
        state,
        {
            "arrived": sim.total_arrived,
            "finished": sim.total_finished,
            "final_available_seats": sim.table.available_count(),
        },
        passed,
        "" if passed else "低流量闭环未完成或座位未恢复",
    )

    # Assert
    assert len(records) == config["simulation_time"]
    assert sim.total_arrived >= 1
    assert sim.total_finished >= 1
    assert sim.table.available_count() == total_capacity(sim)


def test_system_window_queue_pressure_keeps_students_conserved(monkeypatch):
    # Arrange
    config = {
        "simulation_time": 3,
        "window_count": 2,
        "table_rows": 5,
        "table_cols": 5,
        "table_capacity_per_unit": 4,
        "avg_service_time": 3,
        "std_service_time": 0,
        "avg_eating_time": 5,
        "std_eating_time": 0,
    }
    sim = Simulation(**config)
    monkeypatch.setattr(np.random, "poisson", poisson_sequence([8, 0, 0]))
    monkeypatch.setattr(sim, "_sample_service_time", lambda: 3)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 5)

    # Act
    records = list(sim.iter_steps())
    queue_totals = [sum(record["window_queue_lengths"]) for record in records]
    initial_distribution = records[0]["window_queue_lengths"]
    conserved_count = active_student_count(sim)
    passed = (
        sim.total_arrived == 8
        and any(total > 0 for total in queue_totals)
        and abs(initial_distribution[0] - initial_distribution[1]) <= 1
        and conserved_count == sim.total_arrived
    )
    write_artifact(
        "window_queue_pressure_case.json",
        "窗口排队压力场景",
        config,
        records,
        final_state(sim),
        {
            "queue_totals": queue_totals,
            "initial_window_distribution": initial_distribution,
            "conserved_count": conserved_count,
        },
        passed,
        "" if passed else "排队压力场景人数守恒或窗口均衡断言失败",
    )

    # Assert
    assert sim.total_arrived == 8
    assert any(total > 0 for total in queue_totals)
    assert abs(initial_distribution[0] - initial_distribution[1]) <= 1
    assert conserved_count == sim.total_arrived


def test_system_seat_shortage_creates_waiting_queue(monkeypatch):
    # Arrange
    config = {
        "simulation_time": 4,
        "window_count": 2,
        "table_rows": 1,
        "table_cols": 1,
        "table_capacity_per_unit": 1,
        "avg_service_time": 1,
        "std_service_time": 0,
        "avg_eating_time": 5,
        "std_eating_time": 0,
    }
    sim = Simulation(**config)
    monkeypatch.setattr(np.random, "poisson", poisson_sequence([3, 0, 0, 0]))
    monkeypatch.setattr(sim, "_sample_service_time", lambda: 1)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 5)

    # Act
    records = list(sim.iter_steps())
    capacity = total_capacity(sim)
    waiting_counts = [record["waiting_for_seat_count"] for record in records]
    eating_counts = [record["eating_count"] for record in records]
    available_counts = [record["available_seats"] for record in records]
    passed = (
        any(count > 0 for count in eating_counts)
        and any(count > 0 for count in waiting_counts)
        and all(count >= 0 for count in available_counts)
        and all(count <= capacity for count in eating_counts)
    )
    write_artifact(
        "seat_shortage_case.json",
        "座位不足导致等座",
        config,
        records,
        final_state(sim),
        {
            "waiting_counts": waiting_counts,
            "eating_counts": eating_counts,
            "available_counts": available_counts,
            "total_capacity": capacity,
        },
        passed,
        "" if passed else "座位不足场景未产生等座或座位容量越界",
    )

    # Assert
    assert any(count > 0 for count in eating_counts)
    assert any(count > 0 for count in waiting_counts)
    assert all(count >= 0 for count in available_counts)
    assert all(count <= capacity for count in eating_counts)


def test_system_waiting_students_are_reallocated_after_seat_release(monkeypatch):
    # Arrange
    config = {
        "simulation_time": 8,
        "window_count": 1,
        "table_rows": 1,
        "table_cols": 1,
        "table_capacity_per_unit": 1,
        "avg_service_time": 1,
        "std_service_time": 0,
        "avg_eating_time": 2,
        "std_eating_time": 0,
    }
    sim = Simulation(**config)
    monkeypatch.setattr(np.random, "poisson", poisson_sequence([2, 0, 0, 0, 0, 0, 0, 0]))
    monkeypatch.setattr(sim, "_sample_service_time", lambda: 1)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 2)

    # Act
    records = list(sim.iter_steps())
    capacity = total_capacity(sim)
    waiting_counts = [record["waiting_for_seat_count"] for record in records]
    available_counts = [record["available_seats"] for record in records]
    max_waiting_index = waiting_counts.index(max(waiting_counts))
    waiting_dropped_after_peak = any(
        count < waiting_counts[max_waiting_index]
        for count in waiting_counts[max_waiting_index + 1 :]
    )
    passed = (
        max(waiting_counts) > 0
        and waiting_dropped_after_peak
        and sim.total_finished >= 1
        and all(0 <= count <= capacity for count in available_counts)
    )
    write_artifact(
        "waiting_reallocation_case.json",
        "等座学生在座位释放后继续入座",
        config,
        records,
        final_state(sim),
        {
            "waiting_counts": waiting_counts,
            "available_counts": available_counts,
            "waiting_dropped_after_peak": waiting_dropped_after_peak,
        },
        passed,
        "" if passed else "等座队列未在座位释放后下降或座位容量越界",
    )

    # Assert
    assert max(waiting_counts) > 0
    assert waiting_dropped_after_peak
    assert sim.total_finished >= 1
    assert all(0 <= count <= capacity for count in available_counts)


def test_system_logger_records_complete_run_for_analysis(monkeypatch):
    # Arrange
    config = {
        "simulation_time": 5,
        "window_count": 2,
        "table_rows": 2,
        "table_cols": 2,
        "table_capacity_per_unit": 4,
        "avg_service_time": 1,
        "std_service_time": 0,
        "avg_eating_time": 2,
        "std_eating_time": 0,
    }
    sim = Simulation(**config)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = ARTIFACT_DIR / "logger_case.csv"
    logger = DataLogger(file_path=csv_path, total_seats=config["table_rows"] * config["table_cols"] * config["table_capacity_per_unit"])
    monkeypatch.setattr(np.random, "poisson", poisson_sequence([2, 1, 0, 0, 0]))
    monkeypatch.setattr(sim, "_sample_service_time", lambda: 1)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 2)

    # Act
    records = sim.run(data_logger=logger)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    total_entered_values = [int(row["total_entered"]) for row in rows]
    empty_seat_rates = [float(row["empty_seat_rate"]) for row in rows]
    total_queue_counts = [int(row["total_queue_count"]) for row in rows]
    passed = (
        len(records) == config["simulation_time"]
        and csv_path.exists()
        and len(rows) == config["simulation_time"]
        and all(isinstance(record, dict) for record in records)
        and all(0.0 <= rate <= 1.0 for rate in empty_seat_rates)
        and all(count >= 0 for count in total_queue_counts)
        and total_entered_values == sorted(total_entered_values)
    )
    write_artifact(
        "logger_case.json",
        "完整日志记录场景",
        config | {"csv_path": str(csv_path)},
        records,
        final_state(sim),
        {
            "csv_data_rows": len(rows),
            "total_entered_values": total_entered_values,
            "empty_seat_rates": empty_seat_rates,
            "total_queue_counts": total_queue_counts,
        },
        passed,
        "" if passed else "日志行数、空座率或累计进入人数断言失败",
    )

    # Assert
    assert len(records) == config["simulation_time"]
    assert all(isinstance(record, dict) for record in records)
    assert csv_path.exists()
    assert len(rows) == config["simulation_time"]
    assert all(0.0 <= rate <= 1.0 for rate in empty_seat_rates)
    assert all(count >= 0 for count in total_queue_counts)
    assert total_entered_values == sorted(total_entered_values)
