# visualize 模块测试报告

## 一、测试什么
测试对象：SimulationVisualizer 与 RealTimeSimulationVisualizer。

测试目标：
- 函数输入输出正确性：CSV 加载后数据列表是否正确。
- 模块逻辑正确性：实时可视化辅助函数换算与边界截断逻辑是否正确；可视化对象是否可构造。

覆盖项：
- SimulationVisualizer.load_data。
- RealTimeSimulationVisualizer._service_speed_from_time。
- RealTimeSimulationVisualizer._service_time_from_speed。
- RealTimeSimulationVisualizer._clamp。
- RealTimeSimulationVisualizer 构造流程。

## 二、如何测试
测试方式：自动化测试（unittest）。
说明：为避免图形界面依赖，测试中使用 matplotlib 的 Agg 后端。

测试程序：tests/test_visualize_module.py

测试用例设计：
1. test_load_data_from_csv
- 输入：临时 CSV（两条记录）。
- 预期：timestamps=[0,1]，total_queue_counts=[2,3]，empty_seat_rates=[0.75,0.5]。
- 判定：三组列表逐项相等。

2. test_helper_functions
- 输入：avg_service_time=2.0。
- 预期：速度=30.0；逆运算恢复时长约 2.0；clamp(120,0,100)=100。
- 判定：浮点近似相等 + 截断值相等。

3. test_construct_visualizer_without_runtime_error
- 输入：小规模 Simulation 实例。
- 预期：实时可视化器对象可成功创建且不抛异常。
- 判定：对象非空且构造过程完成。

执行命令：
- F:/Anaconda/python.exe -m unittest -v tests/test_visualize_module.py

## 三、实际测试及测试结果
实际结果：
- 共执行 3 个测试用例。
- 通过 3 个，失败 0 个，错误 0 个。
- 测试结论：通过。

关键输出摘录：
- Ran 3 tests in 0.856s
- OK

结论分析：
- 可视化模块核心数据处理逻辑和基础构造流程正确。
- 当前自动化测试聚焦“无界面阻塞场景”，适合持续集成环境。
- 建议后续补充人工交互测试（暂停/重置/滑块/输入框联动）与截图比对测试。
