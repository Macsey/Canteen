"""北京交通大学就餐仿真系统 - 数据记录模块。

该模块提供 DataLogger，用于在仿真每个 Tick 持久化关键指标到 CSV 文件。
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional, TextIO

import config


class DataLogger:
    """仿真数据记录器。

    日志字段：
    - timestamp: 当前 Tick 时间戳。
    - total_entered: 截止当前 Tick 的累计进入人数。
    - total_queue_count: 当前总排队人数。
    - empty_seat_rate: 当前空座率。

    说明：
    - total_queue_count = 各窗口队列规模之和 + 等座人数。
      该定义可以更全面地反映系统拥堵程度。
    """

    HEADER = ["timestamp", "total_entered", "total_queue_count", "empty_seat_rate"]

    def __init__(
        self,
        file_path: str = "simulation_log.csv",
        total_seats: Optional[int] = None,
        overwrite: bool = True,
    ) -> None:
        self.file_path = Path(file_path)
        self.total_seats = (
            total_seats
            if total_seats is not None
            else config.TABLE_ROWS * config.TABLE_COLS * config.TABLE_CAPACITY_PER_UNIT
        )
        self.overwrite = overwrite

        self._file: Optional[TextIO] = None
        self._writer: Optional[csv.writer] = None

    def open(self) -> None:
        """打开日志文件并写入表头。"""
        mode = "w" if self.overwrite else "a"
        write_header = self.overwrite or (not self.file_path.exists()) or self.file_path.stat().st_size == 0

        self._file = self.file_path.open(mode, newline="", encoding="utf-8-sig")
        self._writer = csv.writer(self._file)
        if write_header:
            self._writer.writerow(self.HEADER)

    def log_tick(self, state: Dict[str, object]) -> None:
        """记录单个 Tick 的状态数据。

        参数 state 默认对齐 Simulation.step() 的返回结构。
        """
        if self._writer is None:
            self.open()

        window_queue_lengths = state.get("window_queue_lengths", [])
        if not isinstance(window_queue_lengths, list):
            window_queue_lengths = []

        waiting_for_seat_count = int(state.get("waiting_for_seat_count", 0))
        total_queue_count = sum(int(v) for v in window_queue_lengths) + waiting_for_seat_count

        available_seats = int(state.get("available_seats", 0))
        empty_seat_rate = 0.0 if self.total_seats <= 0 else available_seats / float(self.total_seats)

        row = [
            int(state.get("time", 0)),
            int(state.get("total_arrived", 0)),
            total_queue_count,
            round(empty_seat_rate, 6),
        ]
        self._writer.writerow(row)

    def close(self) -> None:
        """关闭日志文件。"""
        if self._file is not None:
            self._file.close()
            self._file = None
            self._writer = None

    def __enter__(self) -> "DataLogger":
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
