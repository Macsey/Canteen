"""北京交通大学就餐仿真系统 - 核心实体模型。

本模块定义三个核心对象：
1. Student：学生个体，记录从到达、打饭到就餐结束的全过程时间信息。
2. Window：打饭窗口，维护排队队列与当前服务对象。
3. Table：餐桌矩阵，管理座位占用与释放。

说明：
- 该实现仅依赖 Python 标准库，适合作为后续接入可视化（例如 Pygame）的逻辑层。
- 采用 Tick 驱动思想：每调用一次 tick 相关方法，代表时间推进一个离散步长。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import random
from typing import Callable, Deque, Optional, Tuple


@dataclass
class Student:
    """学生实体。

    属性说明：
    - id: 学生唯一编号。
    - arrival_time: 进入食堂的时间点（tick）。
    - service_start_time: 开始打饭的时间点。
    - eating_start_time: 开始就餐的时间点。
    - eating_duration: 计划就餐总时长。

    额外状态字段用于 Tick 更新：
    - status: 当前状态（waiting / serving / waiting_seat / eating / finished）。
    - remaining_service_time: 打饭剩余时长。
    - remaining_eating_time: 就餐剩余时长。
    - seat_position: 就餐座位坐标 (row, col)。
    """

    id: int
    arrival_time: int
    service_start_time: Optional[int] = None
    eating_start_time: Optional[int] = None
    eating_duration: Optional[int] = None

    status: str = "waiting"
    remaining_service_time: int = 0
    remaining_eating_time: int = 0
    seat_position: Optional[Tuple[int, int]] = None

    def start_service(self, current_tick: int, service_duration: int) -> None:
        """进入打饭阶段。"""
        self.service_start_time = current_tick
        self.remaining_service_time = max(1, int(service_duration))
        self.status = "serving"

    def start_eating(
        self,
        current_tick: int,
        eating_duration: int,
        seat_position: Tuple[int, int],
    ) -> None:
        """进入就餐阶段。"""
        self.eating_start_time = current_tick
        self.eating_duration = max(1, int(eating_duration))
        self.remaining_eating_time = self.eating_duration
        self.seat_position = seat_position
        self.status = "eating"

    def update_state_on_tick(self) -> Optional[str]:
        """在一个 Tick 内更新学生状态。

        返回值：
        - "service_finished": 当前 Tick 打饭完成。
        - "eating_finished": 当前 Tick 就餐完成。
        - None: 本 Tick 没有状态终结事件。
        """
        if self.status == "serving":
            self.remaining_service_time -= 1
            if self.remaining_service_time <= 0:
                self.remaining_service_time = 0
                self.status = "waiting_seat"
                return "service_finished"

        if self.status == "eating":
            self.remaining_eating_time -= 1
            if self.remaining_eating_time <= 0:
                self.remaining_eating_time = 0
                self.status = "finished"
                return "eating_finished"

        return None


@dataclass
class Window:
    """打饭窗口实体。

    属性说明：
    - id: 窗口编号。
    - queue: 该窗口等待打饭的学生队列（FIFO）。
    - current_student: 当前正在服务的学生。
    - total_served: 累计已完成服务人数。
    """

    id: int
    queue: Deque[Student] = field(default_factory=deque)
    current_student: Optional[Student] = None
    total_served: int = 0

    def enqueue(self, student: Student) -> None:
        """学生加入该窗口排队队列。"""
        self.queue.append(student)

    def handle_service_tick(
        self,
        current_tick: int,
        service_time_sampler: Callable[[], int],
    ) -> Optional[Student]:
        """处理一个 Tick 的打饭逻辑。

        执行顺序：
        1. 如果窗口空闲且队列非空，拉取下一位学生开始服务。
        2. 对当前服务学生进行 1 Tick 状态推进。
        3. 若该学生本 Tick 完成打饭，返回该学生对象供上层分配座位。

        返回值：
        - 完成打饭的学生对象（需要上层继续安排找座位流程）。
        - None（本 Tick 无学生完成打饭）。
        """
        if self.current_student is None and self.queue:
            next_student = self.queue.popleft()
            next_student.start_service(current_tick, service_time_sampler())
            self.current_student = next_student

        if self.current_student is None:
            return None

        event = self.current_student.update_state_on_tick()
        if event == "service_finished":
            finished_student = self.current_student
            self.current_student = None
            self.total_served += 1
            return finished_student

        return None

    def queue_length(self) -> int:
        """返回窗口总等待规模（含当前服务者）。"""
        return len(self.queue) + (1 if self.current_student is not None else 0)


@dataclass
class Table:
    """餐桌矩阵实体。

    使用二维整数矩阵表示每张桌子的占用人数：
    - 0: 空桌
    - 1~4: 当前该桌就餐人数
    """

    rows: int
    cols: int
    capacity_per_unit: int = 4
    seats: list[list[int]] = field(init=False)

    def __post_init__(self) -> None:
        # 初始化为全空闲（每桌占用人数为 0）
        self.seats = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

    def find_empty_seat(self) -> Optional[Tuple[int, int]]:
        """查找并返回任意一个仍有余位的桌位坐标 (row, col)。"""
        for row in range(self.rows):
            for col in range(self.cols):
                if self.seats[row][col] < self.capacity_per_unit:
                    return row, col
        return None

    def occupy_seat(self, prefer_shared: bool = True) -> Optional[Tuple[int, int]]:
        """占用一个桌位容量并返回其坐标；若全部满员则返回 None。

        参数：
        - prefer_shared: 为 True 时优先拼桌（先选已有就餐者但未满员的桌）。
        """
        candidates = [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
            if self.seats[row][col] < self.capacity_per_unit
        ]
        if not candidates:
            return None

        if prefer_shared:
            shared_candidates = [
                seat
                for seat in candidates
                if 0 < self.seats[seat[0]][seat[1]] < self.capacity_per_unit
            ]
            target_pool = shared_candidates if shared_candidates else candidates
        else:
            target_pool = candidates

        # 使用随机分配避免总是从第一排开始变化，画面更符合真实就餐随机性。
        seat = random.choice(target_pool)
        row, col = seat
        self.seats[row][col] += 1
        return seat

    def release_seat(self, seat_position: Tuple[int, int]) -> bool:
        """释放指定座位。

        返回值：
        - True: 成功释放。
        - False: 坐标非法或该座位本就为空。
        """
        row, col = seat_position
        if row < 0 or row >= self.rows or col < 0 or col >= self.cols:
            return False

        if self.seats[row][col] <= 0:
            return False

        self.seats[row][col] -= 1
        return True

    def available_count(self) -> int:
        """返回当前剩余可用座位总数。"""
        occupied = sum(occupied for row in self.seats for occupied in row)
        return self.rows * self.cols * self.capacity_per_unit - occupied
