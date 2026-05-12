from __future__ import annotations

import csv

import numpy as np

from logger import DataLogger
from models import Student, Table, Window
from simulation import Simulation

from .helpers import ARTIFACT_DIR


def test_student_window_service_flow():
    # Arrange
    student = Student(id=1, arrival_time=0)
    window = Window(id=0)

    # Act
    window.enqueue(student)
    queued_length = window.queue_length()
    finished_student = window.handle_service_tick(
        current_tick=0,
        service_time_sampler=lambda: 1,
    )

    # Assert
    assert queued_length == 1
    assert finished_student is student
    assert finished_student.status == "waiting_seat"
    assert window.current_student is None
    assert window.total_served == 1
    assert window.queue_length() == 0


def test_finished_service_student_can_be_allocated_to_table():
    # Arrange
    table = Table(rows=1, cols=1, capacity_per_unit=2)
    student = Student(id=1, arrival_time=0, status="waiting_seat")
    before_available = table.available_count()

    # Act
    seat = table.occupy_seat()
    student.start_eating(current_tick=1, eating_duration=3, seat_position=seat)

    # Assert
    assert before_available == 2
    assert seat is not None
    assert student.status == "eating"
    assert student.seat_position == seat
    assert student.eating_start_time == 1
    assert student.eating_duration == 3
    assert table.available_count() == 1


def test_table_release_seat_handles_success_duplicate_and_invalid_positions():
    # Arrange
    table = Table(rows=1, cols=1, capacity_per_unit=1)
    seat = table.occupy_seat()

    # Act
    available_after_occupy = table.available_count()
    first_release = table.release_seat(seat)
    available_after_release = table.available_count()
    duplicate_release = table.release_seat(seat)
    invalid_release = table.release_seat((99, 99))

    # Assert
    assert seat == (0, 0)
    assert available_after_occupy == 0
    assert first_release is True
    assert available_after_release == 1
    assert duplicate_release is False
    assert invalid_release is False


def test_simulation_generate_students_balances_window_queues(monkeypatch):
    # Arrange
    sim = Simulation(simulation_time=5, window_count=2, table_rows=1, table_cols=1)
    monkeypatch.setattr(np.random, "poisson", lambda _arrival_lambda: 4)

    # Act
    arrived_count = sim.generate_students(current_time=0, arrival_lambda=4)
    queue_lengths = [window.queue_length() for window in sim.windows]

    # Assert
    assert arrived_count == 4
    assert sim.total_arrived == 4
    assert sum(queue_lengths) == 4
    assert abs(queue_lengths[0] - queue_lengths[1]) <= 1


def test_simulation_update_windows_allocates_finished_student_to_table(monkeypatch):
    # Arrange
    sim = Simulation(
        simulation_time=5,
        window_count=1,
        table_rows=1,
        table_cols=1,
        table_capacity_per_unit=1,
    )
    student = Student(id=1, arrival_time=0)
    sim.windows[0].enqueue(student)
    monkeypatch.setattr(sim, "_sample_service_time", lambda: 1)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 3)

    # Act
    sim.update_windows(current_time=0)

    # Assert
    assert len(sim.eating_students) == 1
    assert sim.eating_students[0] is student
    assert student.status == "eating"
    assert student.eating_duration == 3
    assert len(sim.waiting_for_seat) == 0
    assert sim.table.available_count() == 0


def test_simulation_update_windows_moves_finished_student_to_waiting_queue_when_no_seat(monkeypatch):
    # Arrange
    sim = Simulation(
        simulation_time=5,
        window_count=1,
        table_rows=1,
        table_cols=1,
        table_capacity_per_unit=1,
    )
    occupied_seat = sim.table.occupy_seat()
    student = Student(id=1, arrival_time=0)
    sim.windows[0].enqueue(student)
    monkeypatch.setattr(sim, "_sample_service_time", lambda: 1)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 3)

    # Act
    sim.update_windows(current_time=0)

    # Assert
    assert occupied_seat == (0, 0)
    assert len(sim.eating_students) == 0
    assert len(sim.waiting_for_seat) == 1
    assert sim.waiting_for_seat[0] is student
    assert student.status == "waiting_seat"
    assert sim.table.available_count() == 0


def test_simulation_update_tables_releases_finished_seat_and_reallocates_waiting_student(monkeypatch):
    # Arrange
    sim = Simulation(
        simulation_time=5,
        window_count=1,
        table_rows=1,
        table_cols=1,
        table_capacity_per_unit=1,
    )
    student_a = Student(id=1, arrival_time=0)
    student_b = Student(id=2, arrival_time=0, status="waiting_seat")
    seat = sim.table.occupy_seat()
    student_a.start_eating(current_tick=0, eating_duration=1, seat_position=seat)
    sim.eating_students.append(student_a)
    sim.waiting_for_seat.append(student_b)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 3)

    # Act
    sim.update_tables(current_time=1)

    # Assert
    assert student_a.status == "finished"
    assert sim.total_finished == 1
    assert len(sim.eating_students) == 1
    assert sim.eating_students[0].id == student_b.id
    assert student_b.status == "eating"
    assert student_b.eating_duration == 3
    assert len(sim.waiting_for_seat) == 0
    assert sim.table.available_count() == 0


def test_simulation_step_returns_stable_stats_schema(monkeypatch):
    # Arrange
    sim = Simulation(
        simulation_time=3,
        window_count=2,
        table_rows=1,
        table_cols=1,
        table_capacity_per_unit=2,
        avg_service_time=1,
        std_service_time=0,
        avg_eating_time=2,
        std_eating_time=0,
    )
    monkeypatch.setattr(np.random, "poisson", lambda _arrival_lambda: 1)
    monkeypatch.setattr(sim, "_sample_service_time", lambda: 1)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 2)
    required_keys = [
        "time",
        "arrived_this_tick",
        "departed_this_tick",
        "total_arrived",
        "total_finished",
        "waiting_for_seat_count",
        "eating_count",
        "available_seats",
        "window_queue_lengths",
        "current_arrival_rate",
        "avg_service_time",
        "avg_eating_time",
    ]

    # Act
    stats = sim.step()

    # Assert
    assert isinstance(stats, dict)
    assert all(key in stats for key in required_keys)
    assert stats["time"] == 0
    assert isinstance(stats["window_queue_lengths"], list)
    assert isinstance(stats["available_seats"], int)
    assert isinstance(stats["current_arrival_rate"], float)
    assert stats["total_arrived"] >= stats["arrived_this_tick"]
    assert stats["total_finished"] >= stats["departed_this_tick"]


def test_simulation_run_writes_csv_through_data_logger(monkeypatch):
    # Arrange
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = ARTIFACT_DIR / "interface_run_log.csv"
    logger = DataLogger(file_path=csv_path, total_seats=1, overwrite=True)
    sim = Simulation(
        simulation_time=3,
        window_count=1,
        table_rows=1,
        table_cols=1,
        table_capacity_per_unit=1,
        avg_service_time=1,
        std_service_time=0,
        avg_eating_time=1,
        std_eating_time=0,
    )
    monkeypatch.setattr(np.random, "poisson", lambda _arrival_lambda: 1)
    monkeypatch.setattr(sim, "_sample_service_time", lambda: 1)
    monkeypatch.setattr(sim, "_sample_eating_time", lambda: 1)

    # Act
    records = sim.run(data_logger=logger)

    # Assert
    assert len(records) == 3
    assert csv_path.exists()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    assert rows[0] == ["timestamp", "total_entered", "total_queue_count", "empty_seat_rate"]
    assert len(rows) == 4
