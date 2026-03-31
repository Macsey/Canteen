# config 模块测试报告

## 一、测试什么
测试对象：配置模块中的全局参数常量。

测试目标：
- 函数/模块输入输出正确性：本模块无函数输入输出，重点验证配置值本身有效。
- 模块逻辑正确性：确认关键参数满足仿真运行的基础约束（必须为正值）。

覆盖项：
- SIMULATION_TIME、WINDOW_COUNT、TABLE_ROWS、TABLE_COLS、TABLE_CAPACITY_PER_UNIT。
- ARRIVAL_RATE、AVG_SERVICE_TIME、AVG_EATING_TIME。
- ARRIVAL_PEAK_FACTOR、ARRIVAL_OFFPEAK_FACTOR。

## 二、如何测试
测试方式：自动化测试（unittest）。

测试程序：tests/test_config_module.py

测试用例设计：
1. test_basic_numeric_constraints
- 输入数据：直接读取模块默认常量。
- 预期输出：上述数值均大于 0。
- 判定标准：若任一值 <= 0，则该用例失败。

2. test_peak_offpeak_factors_are_positive
- 输入数据：ARRIVAL_PEAK_FACTOR、ARRIVAL_OFFPEAK_FACTOR。
- 预期输出：二者均 > 0。
- 判定标准：任一因子 <= 0 则失败。

执行命令：
- F:/Anaconda/python.exe -m unittest -v tests/test_config_module.py

## 三、实际测试及测试结果
实际结果：
- 共执行 2 个测试用例。
- 通过 2 个，失败 0 个，错误 0 个。
- 测试结论：通过。

关键输出摘录：
- Ran 2 tests in 0.001s
- OK

结论分析：
- 当前配置参数满足最基本的数值有效性约束，具备进入仿真流程的前置条件。
- 本模块后续可扩展测试：参数上下界合理性（例如窗口数过大/过小场景）与参数组合一致性校验。
