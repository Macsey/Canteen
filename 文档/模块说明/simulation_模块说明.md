# simulation.py 模块代码说明文档

## 1. 模块概述
`simulation.py` 是**北京交通大学就餐仿真系统**的“仿真引擎（驱动模块）”。在上一层 `models.py` 定义了物理实体的前提下，`Simulation` 类负责将其组装起来，利用离散的时间步（Tick）持续推进系统：生成人流抵达、维护各窗口打餐作业、维护就餐作业并统计每一帧的状态。

## 2. 核心类解析

### 2.1 `SimulationStats`
这是一个利用 `@dataclass` 定义的数据传输对象（DTO），它仅仅用于包装**单个 Tick 切面下**的系统所有统计指标（例如当前排队人数、此刻生成的到达率、吃完及到达的人数等）。它提供 `to_dict()` 以便于序列化，抛给 `logger` 存 CSV 或给可视化模块动态取用。

### 2.2 `Simulation` 类
仿真主类。整合所有实体调度与随机过程采样。

#### **模块初始化 (`__init__`)**
- 内部会接管并在开始时克隆所有通过构造器传入的参数（兜底从 `config` 读取）。
- 初始化若干窗口 `Window` 组成的列表，以及一个总览 `Table`。
- 构建各种容器，如 `waiting_for_seat` 等座队列、`eating_students` 正在吃饭的池子、以及累加时间用作均值展现的列表 `sampled_service_times` 等。

#### **随机采样与生成**
- **时间生成 (`_sample_positive_normal`)**: 通过 `random.gauss` 为每个学生单独抽取正态分布耗时并截断负数。
- **动态到达率 (`_current_arrival_rate`)**: 一个非常关键的方法。它利用正弦函数 `np.sin()` 将总体仿真时间映射为一个类似于现实早/午/晚高峰**“缓慢上升 -> 峰值 -> 缓慢回落”**的 $\lambda$ 强度调节曲线。
- **学生生成 (`generate_students`)**: 每 Tick 依照泊松分布（`np.random.poisson`）算出这一秒有几个学生到来，为他们分配唯一 ID，并将之分流给负载最轻的窗口（`_choose_least_loaded_window`）。

#### **生命周期演进 (Update流程)**
- **`update_windows()`**: 唤起每个窗口的 Tick，并处理从窗口释放出打完饭的学生。尝试将其调用 `_try_allocate_seat`，如果不成功（满座）则必须加入至 `waiting_for_seat` 等座队列。
- **`update_tables()`**: 处理就餐的 Tick。
  1. 迭代筛选 `eating_students`，将吃够时间的学生踢出并调用 `table.release_seat()`，累加系统 `total_finished` 计数。
  2. 把腾出席位后，从 `waiting_for_seat` 队列按顺序消化等座人员填补到空位上。

#### **外部调用接口 (Simulation 循环流)**
设计了极其优雅的多种调用模式，以适应离线与实时应用：
- **`step()`**: 一次执行内部各项的 Update，并且把当前总状返回出去（`SimulationStats.to_dict()`）。如果超时则抛 `StopIteration`。
- **`iter_steps()`**: 将 `step` 封装在生成器 `yield` 中，对于诸如 Matplotlib `FuncAnimation` 非常友好。
- **`run(data_logger)`**: 提供传统的“一键黑盒运行”到底功能。自动开启日志上下文并消费空仿真直到指定时间步结束，然后统一返回结果列表。

## 3. 设计亮点
- **随机过程应用得当**：巧妙的结合了现实社会现象中的两种最典型分布：到达时间使用泊松随机生成、耗费时长使用正态随机生成，且加入基于时间的波峰曲线，极其逼真地还原了系统压力测试指标。
- **无头设计 (Headless)**：该引擎本身绝对独立于任何前端库，使得你可以轻松将此项目重构以运行于 Pygame、网页、终端图表乃至云端服务上。