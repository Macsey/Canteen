"""北京交通大学就餐仿真系统 - 仿真驱动模块。

本模块提供 Simulation 类，负责按 Tick 推进整个系统：
1. 生成到达学生（泊松过程）；
2. 更新窗口服务状态；
3. 更新就餐区状态；
4. 输出每个时间步的统计信息。

设计目标：
- 核心逻辑与展示层解耦，便于后续接入 Pygame 等可视化模块；
- 提供 step() 与 iter_steps() 两种驱动方式，分别适合离散调用和逐帧渲染。
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Generator, List, Optional, TYPE_CHECKING

import numpy as np

import config
from models import Student, Table, Window

if TYPE_CHECKING:
    from logger import DataLogger


@dataclass
class SimulationStats:
    """单个 Tick 的统计快照。"""

    time: int
    arrived_this_tick: int
    departed_this_tick: int
    total_arrived: int
    total_finished: int
    waiting_for_seat_count: int
    eating_count: int
    available_seats: int
    window_queue_lengths: List[int]
    current_arrival_rate: float
    avg_service_time: float
    avg_eating_time: float

    def to_dict(self) -> Dict[str, object]:
        """转换为字典，便于日志记录、JSON 序列化或可视化层消费。"""
        return {
            "time": self.time,
            "arrived_this_tick": self.arrived_this_tick,
            "departed_this_tick": self.departed_this_tick,
            "total_arrived": self.total_arrived,
            "total_finished": self.total_finished,
            "waiting_for_seat_count": self.waiting_for_seat_count,
            "eating_count": self.eating_count,
            "available_seats": self.available_seats,
            "window_queue_lengths": self.window_queue_lengths,
            "current_arrival_rate": round(self.current_arrival_rate, 3),
            "avg_service_time": round(self.avg_service_time, 3),
            "avg_eating_time": round(self.avg_eating_time, 3),
        }


class Simulation:
    """就餐系统仿真器（Tick-based）。"""

    def __init__(
        self,
        simulation_time: int = config.SIMULATION_TIME,
        window_count: int = config.WINDOW_COUNT,
        table_rows: int = config.TABLE_ROWS,
        table_cols: int = config.TABLE_COLS,
        table_capacity_per_unit: int = config.TABLE_CAPACITY_PER_UNIT,
        arrival_rate: float = config.ARRIVAL_RATE,
        arrival_peak_factor: float = config.ARRIVAL_PEAK_FACTOR,
        arrival_offpeak_factor: float = config.ARRIVAL_OFFPEAK_FACTOR,
        avg_service_time: float = config.AVG_SERVICE_TIME,
        std_service_time: float = config.STD_SERVICE_TIME,
        avg_eating_time: float = config.AVG_EATING_TIME,
        std_eating_time: float = config.STD_EATING_TIME,
    ) -> None:
        """初始化仿真配置与实体对象。"""
        self.simulation_time = int(simulation_time)
        self.arrival_rate = float(arrival_rate)
        self.arrival_peak_factor = float(arrival_peak_factor)
        self.arrival_offpeak_factor = float(arrival_offpeak_factor)
        self.avg_service_time = float(avg_service_time)
        self.std_service_time = float(std_service_time)
        self.avg_eating_time = float(avg_eating_time)
        self.std_eating_time = float(std_eating_time)

        self.windows: List[Window] = [Window(id=i) for i in range(window_count)]
        self.table = Table(rows=table_rows, cols=table_cols, capacity_per_unit=table_capacity_per_unit)

        self.current_time = 0
        self.next_student_id = 1

        self.total_arrived = 0
        self.total_finished = 0

        self.waiting_for_seat: Deque[Student] = deque()
        self.eating_students: List[Student] = []

        # 记录实际采样时长，用于输出动态统计均值。
        self.sampled_service_times: List[int] = []
        self.sampled_eating_times: List[int] = []

    def _sample_positive_normal(self, mean: float, std: float) -> int:
        """采样正态分布并截断为正整数时长。"""
        sampled = random.gauss(mean, std)
        return max(1, int(round(sampled)))

    def _sample_service_time(self) -> int:
        """采样一次打饭时长。"""
        sampled = self._sample_positive_normal(self.avg_service_time, self.std_service_time)
        self.sampled_service_times.append(sampled)
        return sampled

    def _sample_eating_time(self) -> int:
        """采样一次就餐时长。"""
        sampled = self._sample_positive_normal(self.avg_eating_time, self.std_eating_time)
        self.sampled_eating_times.append(sampled)
        return sampled

    def _choose_least_loaded_window(self) -> Window:
        """选择当前排队规模最小的窗口（含正在服务者）。"""
        return min(self.windows, key=lambda window: window.queue_length())

    def _current_arrival_rate(self, current_time: int) -> float:
        """基于仿真进度生成先升后降的平滑到达率。"""
        if self.simulation_time <= 0:
            return self.arrival_rate

        progress = current_time / self.simulation_time
        progress = min(1.0, max(0.0, progress))

        # 使用半周期正弦构造“缓慢上升 -> 峰值 -> 缓慢回落”的人流趋势。
        wave = np.sin(np.pi * progress)
        factor = self.arrival_offpeak_factor + (self.arrival_peak_factor - self.arrival_offpeak_factor) * wave

        return max(0.1, self.arrival_rate * factor)

    def _try_allocate_seat(self, student: Student, current_time: int) -> bool:
        """尝试为学生分配座位并启动就餐流程。"""
        seat = self.table.occupy_seat()
        if seat is None:
            return False

        student.start_eating(
            current_tick=current_time,
            eating_duration=self._sample_eating_time(),
            seat_position=seat,
        )
        self.eating_students.append(student)
        return True

    def generate_students(self, current_time: int, arrival_lambda: Optional[float] = None) -> int:
        """按泊松到达过程生成学生并分配到最短队列窗口。

        说明：
        - 使用 numpy.random.poisson(lambda) 生成当前 Tick 的到达人数。
        - 每位新到学生会被分配到当前排队人数最少的窗口。

        关于“同行人”扩展思路：
        - 可在学生生成时，以 20% 概率创建一个 group_id，表示该学生属于同行组。
        - 同组学生可绑定到同一窗口、并在分配座位时优先尝试邻近空位或同一张桌。
        - 若座位策略支持多人同时入座，可将 waiting_for_seat 从单人队列改为“组队列”。
        """
        if arrival_lambda is None:
            arrival_lambda = self._current_arrival_rate(current_time)
        arrived_count = int(np.random.poisson(arrival_lambda))
        for _ in range(arrived_count):
            student = Student(id=self.next_student_id, arrival_time=current_time)
            self.next_student_id += 1

            target_window = self._choose_least_loaded_window()
            target_window.enqueue(student)

        self.total_arrived += arrived_count
        return arrived_count

    def update_windows(self, current_time: int) -> None:
        """推进所有窗口的服务状态，并将完成打饭者送入就餐流程。"""
        for window in self.windows:
            finished_student = window.handle_service_tick(
                current_tick=current_time,
                service_time_sampler=self._sample_service_time,
            )
            if finished_student is None:
                continue

            # 打饭完成后优先尝试立即安排座位；若无空位则进入等座队列。
            allocated = self._try_allocate_seat(finished_student, current_time)
            if not allocated:
                self.waiting_for_seat.append(finished_student)

    def update_tables(self, current_time: int) -> None:
        """更新就餐区状态：离场释放座位，并尝试安置等座学生。"""
        remaining_eating_students: List[Student] = []

        for student in self.eating_students:
            # 按需求显式使用“开始时间 + 就餐时长”判定就餐结束。
            if (
                student.eating_start_time is not None
                and student.eating_duration is not None
                and current_time >= student.eating_start_time + student.eating_duration
            ):
                if student.seat_position is not None:
                    self.table.release_seat(student.seat_position)
                student.status = "finished"
                self.total_finished += 1
                continue

            remaining_eating_students.append(student)

        self.eating_students = remaining_eating_students

        # 有空位时，按 FIFO 给等座学生安排座位。
        while self.waiting_for_seat and self.table.available_count() > 0:
            student = self.waiting_for_seat.popleft()
            allocated = self._try_allocate_seat(student, current_time)
            if not allocated:
                # 理论上不应发生；若发生则回退并退出，避免忙等。
                self.waiting_for_seat.appendleft(student)
                break

    def step(self) -> Dict[str, object]:
        """执行一个时间步并返回当前统计数据。"""
        if self.current_time >= self.simulation_time:
            raise StopIteration("仿真已结束，无法继续 step。")

        current_time = self.current_time
        current_arrival_rate = self._current_arrival_rate(current_time)
        arrived_this_tick = self.generate_students(current_time, current_arrival_rate)
        self.update_windows(current_time)

        finished_before = self.total_finished
        self.update_tables(current_time)
        departed_this_tick = self.total_finished - finished_before

        sampled_service_mean = (
            sum(self.sampled_service_times) / len(self.sampled_service_times)
            if self.sampled_service_times
            else self.avg_service_time
        )
        sampled_eating_mean = (
            sum(self.sampled_eating_times) / len(self.sampled_eating_times)
            if self.sampled_eating_times
            else self.avg_eating_time
        )

        stats = SimulationStats(
            time=current_time,
            arrived_this_tick=arrived_this_tick,
            departed_this_tick=departed_this_tick,
            total_arrived=self.total_arrived,
            total_finished=self.total_finished,
            waiting_for_seat_count=len(self.waiting_for_seat),
            eating_count=len(self.eating_students),
            available_seats=self.table.available_count(),
            window_queue_lengths=[window.queue_length() for window in self.windows],
            current_arrival_rate=current_arrival_rate,
            avg_service_time=sampled_service_mean,
            avg_eating_time=sampled_eating_mean,
        )

        self.current_time += 1
        return stats.to_dict()

    def iter_steps(self) -> Generator[Dict[str, object], None, None]:
        """逐 Tick 生成统计数据，适合可视化模块逐帧消费。"""
        while self.current_time < self.simulation_time:
            yield self.step()

    def run(self, data_logger: Optional["DataLogger"] = None) -> List[Dict[str, object]]:
        """执行完整仿真主循环并返回全程统计序列。

        参数：
        - data_logger: 可选外部日志器；若不传入则默认记录到 simulation_log.csv。
        """
        if data_logger is None:
            # 延迟导入，避免在仅做模型测试时强依赖日志模块。
            from logger import DataLogger

            active_logger: DataLogger = DataLogger()
        else:
            active_logger = data_logger

        records: List[Dict[str, object]] = []
        with active_logger:
            while self.current_time < self.simulation_time:
                stats = self.step()
                active_logger.log_tick(stats)
                records.append(stats)
        return records
