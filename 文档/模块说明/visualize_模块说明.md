# visualize.py 模块代码说明文档

## 1. 模块概述
`visualize.py` 是**北京交通大学就餐仿真系统**的图形可视化模块。该模块依赖 `matplotlib` 库来分析并呈现系统拥堵情况。
它包含了两种维度的洞察能力：
1. **`SimulationVisualizer` (离线看板)**: 运行仿真落地 CSV 日志后，进行结果的回放和静态图表查阅。
2. **`RealTimeSimulationVisualizer` (实时监控室)**: 融合仪表盘、动图与交互面板的复杂实现，直接接管仿真进程实时运行反馈监控。

## 2. 核心类与交互解析

### 2.1 离线可视化模式 (`SimulationVisualizer`)
这是一个数据分析对象，它的职责非常直接：
- **`load_data()`**: 调用标准库 `csv.DictReader` 处理离线的 `simulation_log.csv` 到内存数组。
- **`plot_queue_trend()` / `plot_empty_seat_rate_trend()`**: 采用 matplotlib 将 `[时间戳 - 总排队人数]`，以及 `[时间戳 - 系统空座率]` 绘制到独立的画布以供检阅。
- 主要用于项目汇报展示整体运行走势或对照两组超参前后的系统表现（离线实验对比分析）。

### 2.2 实时监控系统 (`RealTimeSimulationVisualizer`)
这是系统在可视化层面最有张力的应用，使用了复杂的 `GridSpec` 布局。

#### **UI 与面板组成**
分为四大图块 (子图 Axes)：
1. **排队情况 (右上角, 柱状图)**:
   - 使用 `ax.bar` 展示动态各窗口的排队量，柱子上下跳动。
2. **座位热力图 (左上角, Imshow)**:
   - 读取二手的矩阵映射（$0 \sim 4$ 的不同占用）。利用 `ListedColormap` 构建了从白色、然后至浅绿至红色的阈值阶梯渲染模式，直观展现了食堂座位随着时间聚集的分布。
3. **客流统计表 (下层全宽, Table)**:
   - 滚动显示最靠后的 $10$ 个时间片段的数据，等价于一个动态运行的仪表日志表盘 `ax.table`。
4. **控制台 (左下至中下)**:
   - 包含了一大堆 `Button`, `Slider`, `TextBox`，构筑了高度复杂的交互控制系统。

#### **事件触发架构**
- **仿真推进**: 在 `__init__` 中把传入的 `Simulation` 用 `sim.iter_steps()` 保存为生成器句柄。由于传递给了 `animation.FuncAnimation(...)`，matplotlib 自己的主循环通过内部的一个 `Timer` 事件会不断调配它的 `_update()` 核心帧方法，从中抛最新的一帧模型数据并覆盖刷新 UI（例如 `bar.set_height()` 等）。
- **人机交互**:
  - `_on_pause_clicked` / `_on_reset_clicked`: 单击暂停标志位；单击重置将清除历史缓存并生成新的环境对象覆盖进去。
  - `_on_slider_changed` & `_on_text_submit` 组件联动：拖曳滑块将修改底层 `sim` 挂载的时间系数（到达率、服务时间等），实现在仿真期间**动态注入热修改压力**的效果。由于 TextBox 和 Slider 互相关联修改，做了一个 `_syncing_text` 原子锁标记以避免死循环。

## 3. 设计亮点
- **强大的 Matplotlib API 掌握**：突破了传统的简单 plot 用法，结合了动画系统 `FuncAnimation` 配合多子图和表单等低频组件完成了一个综合仪表盘开发。
- **热更新修改设计**：能让你在“午餐高峰正要到来”时刻临时放平服务员的打饭倍率（假装系统宕机），直观观测到热力图由绿转红的过程，提升了仿真工具极强的人机展示体验性。