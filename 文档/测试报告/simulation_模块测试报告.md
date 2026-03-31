# simulation 模块测试报告

## 一、测试什么
测试对象：Simulation 类的到达生成、单步推进和完整运行。

测试目标：
- 函数输入输出正确性：step 返回字段是否完整，run 返回记录数是否正确。
- 模块逻辑正确性：时间推进、学生生成计数、日志联动是否正确。

覆盖项：
- generate_students。
- step。
- run（含 DataLogger 联动）。

## 二、如何测试
测试方式：自动化测试（unittest + mock）。

测试程序：tests/test_simulation_module.py

测试用例设计：
1. test_generate_students_count
- 输入：mock numpy.random.poisson 固定返回 3。
- 预期：arrived=3，total_arrived=3，各窗口队列总和=3。
- 判定：三项计数全部一致。

2. test_step_output_schema_and_time_progress
- 输入：mock poisson=2，mock random.gauss=2.0。
- 预期：step 返回包含 12 个关键字段，time=0，sim.current_time 推进到 1。
- 判定：字段集合包含关系成立且时间推进正确。

3. test_run_produces_records_and_log
- 输入：simulation_time=5，临时日志文件路径，mock poisson=1，mock gauss=2.0。
- 预期：run 返回 5 条记录，并实际生成 CSV 日志文件。
- 判定：len(records)=5 且日志文件存在。

执行命令：
- F:/Anaconda/python.exe -m unittest -v tests/test_simulation_module.py

## 三、实际测试及测试结果
实际结果：
- 共执行 3 个测试用例。
- 通过 3 个，失败 0 个，错误 0 个。
- 测试结论：通过。

关键输出摘录：
- Ran 3 tests in 0.074s
- OK

结论分析：
- 仿真主引擎在“生成-推进-记录”链路上的核心逻辑正确。
- 字段口径与模块接口稳定，可供日志和可视化直接消费。
- 建议后续追加长时仿真（大于1000 Tick）的性能和内存占用测试。
