# logger.py 模块代码说明文档

## 1. 模块概述
`logger.py` 是**北京交通大学就餐仿真系统**的数据记录模块。它的主要作用是提供一个数据日志记录器 `DataLogger`，用于在仿真进行的每一个 Tick 步长内，持久化关键统计指标到 CSV 文件，从而为后续的离线分析及可视化打下基础。

## 2. 核心类与方法解析

### 2.1 `DataLogger` 类
此类负责打开、写入与关闭 CSV 文件。

#### **类属性**
- **`HEADER`**: 定义了 CSV 导出的表头结构：`["timestamp", "total_entered", "total_queue_count", "empty_seat_rate"]`。
  - `timestamp`: 当前系统 Tick 时间戳。
  - `total_entered`: 截止到当前 Tick 累计进入食堂的总人数。
  - `total_queue_count`: 当前总排队人数（包括各窗口队列人数及等座的人数）。
  - `empty_seat_rate`: 当前食堂的空座率。

#### **初始化 `__init__`**
- 支持传入目标文件路径 `file_path`（默认 `simulation_log.csv`）。
- 支持传入系统总座位数 `total_seats`；若不传，则自动读取 `config` 模块的 `TABLE_ROWS * TABLE_COLS * TABLE_CAPACITY_PER_UNIT` 计算得出。
- `overwrite` 参数控制是以覆盖模式(`w`) 还是追加模式(`a`) 写入。

#### **核心方法**
- **`open(self)`**: 打开日志文件。如果没有数据，会先写入表头 `HEADER`。
- **`log_tick(self, state: Dict[str, object])`**: 记录单个 Tick 的数据。
  - 参数 `state` 是由 `Simulation.step()` 返回的数据快照字典。
  - 它会从 `state` 中提取 `window_queue_lengths`（各窗口队列）、`waiting_for_seat_count`（等座人数）以计算总排队规模；提取 `available_seats` 计算出准确的 `empty_seat_rate`（空座率）。
  - 处理完的数据会作为一行记录写入 CSV。
- **`close(self)`**: 关闭文件句柄，释放系统资源。

#### **上下文管理器支持**
- 实现了 `__enter__` 和 `__exit__` 魔法方法。这使得 `DataLogger` 能够以 `with DataLogger() as logger:` 的形式使用，在出作用域时自动调用 `close()`，从而确保文件安全落盘，避免数据丢失。

## 3. 架构意义
- **解耦输出与运算**：核心仿真引擎 `Simulation` 只负责产生状态 `state` 字典，而不关心应该怎么存。`DataLogger` 则负责将状态持久化，符合单一职责原则。
- **可扩展性**：若后续需要记录更多的指标（如“学生平均等待时长”等），只需在 `HEADER` 和 `log_tick` 中增补即可。