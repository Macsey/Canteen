# models.py 模块代码说明文档

## 1. 模块概述
`models.py` 是**北京交通大学就餐仿真系统**的核心实体模型模块。它以 Python 的 `dataclass` 构建了仿真环境中的三个基本业务实体定义：`Student`（学生个体）、`Window`（打饭窗口）和 `Table`（餐桌矩阵）。
本模块完全基于 Python 标准库，采用了 **Tick 驱动**（离散时间步）的思想，作为纯逻辑层便于灵活接入任何表现形式（文本、图表、Pygame 等）。

## 2. 核心类解析

### 2.1 `Student` (学生实体)
表示进入食堂就餐的学生微观个体，记录其活动全生命周期。
- **基本属性**:
  - `id`: 学生唯一标识；`arrival_time`: 进入系统的 Tick；其它如开始打饭/就餐时间、应耗时长起初为 `None`。
- **状态维护**:
  - `status`: 在生命周期上流转：`waiting` (排队打饭) -> `serving` (正在打饭) -> `waiting_seat` (排队等座) -> `eating` (就餐中) -> `finished` (离场)。
  - `remaining_service_time` / `remaining_eating_time`: 用于在仿真过程中倒计时。
- **关键方法**:
  - `start_service(...)` / `start_eating(...)`: 在特定 Tick 被触发，注入耗时与位置信息并变更初始状态。
  - **`update_state_on_tick(self)`**: 驱动学生状态在单个 Tick 内前进一步。它会对剩余的“打饭时间”或“就餐时间”扣减 1，如果减到 0 则抛出状态变更事件（如 `"service_finished"` 或 `"eating_finished"`）。

### 2.2 `Window` (打饭窗口实体)
表示食堂单一的打饭队列管理设施。
- **属性**:
  - `id`: 唯一编号；`queue`: 等待队列，使用 `collections.deque` 实现高效的 FIFO（先进先出）。
  - `current_student`: 窗口当前正在处理的学生。
  - `total_served`: 统计该窗口服务总人数。
- **关键方法**:
  - `enqueue(student)`: 新到达的学生被追加到队尾。
  - **`handle_service_tick(...)`**: 处理单次 Tick 的核心函数。
    1. 如果当前为空且队列有人，则取队列第一名开始服务。
    2. 调用当前学生的 `update_state_on_tick()`。
    3. 如果该学生该 Tick 恰好打餐完毕，将当前学生指针置空并返回该学生对象（丢给上层设施去安排座位）。
  - `queue_length()`: 计算窗口负载量（队列长度 + 正在打饭的 1 人）。

### 2.3 `Table` (餐桌矩阵实体)
负责管理整个就餐区的座位情况，采用二维数组建模。
- **属性**:
  - `rows`, `cols`: 矩阵行列数；`capacity_per_unit`: 每桌最大支持就餐人数。
  - `seats`: 初始化生成的全 `0` 二维矩阵，表示无人落座。
- **关键方法**:
  - `find_empty_seat()`: 寻找任意一张未坐满的桌子。
  - **`occupy_seat(prefer_shared=True)`**: 执行入座操作并返回座位坐标 `(row, col)`。策略上支持 `prefer_shared` (倾向于“拼桌”)；挑选空位时使用了 `random.choice()`，避免由于按顺序便利导致的座位占用集中在左上角的非真实情况。
  - `release_seat(...)`: 接收坐标并将该桌就餐人数 -1。
  - `available_count()`: 遍历计算整个餐厅还能容纳的剩余入座人数。

## 3. 设计亮点
- **微观仿真 (Agent-Based Modeling)**：没有采用宏观数值公式，而是追踪每一个独立个体的生命周期，使得排队与抢座现象自然涌现（Emergence）。
- **去中心化状态流转**：系统通过分发 Tick 给每个人和窗口，个体自治更新剩余时间并报告自身完结，极大简化了上层主循环的复杂性。