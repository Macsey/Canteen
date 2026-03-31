# logger 模块测试报告

## 一、测试什么
测试对象：DataLogger 日志记录器。

测试目标：
- 函数输入输出正确性：log_tick 写入字段值是否与输入状态一致。
- 模块逻辑正确性：表头写入、队列总人数计算、追加写模式是否正确。

覆盖项：
- open / log_tick / close / 上下文管理。
- overwrite=True 和 overwrite=False 两种模式。

## 二、如何测试
测试方式：自动化测试（unittest）。

测试程序：tests/test_logger_module.py

测试用例设计：
1. test_logger_header_and_single_row
- 输入：构造状态字典（time=1,total_arrived=10,window_queue_lengths=[2,1,0],waiting_for_seat_count=3,available_seats=10,total_seats=20）。
- 预期：
  - 表头等于 DataLogger.HEADER。
  - 数据行为 [1,10,6,0.5]（排队总人数=2+1+0+3=6，空座率=10/20=0.5）。
- 判定：CSV 内容逐字段比对。

2. test_logger_append_mode
- 输入：先 overwrite=True 写入一行，再 overwrite=False 追加一行。
- 预期：最终 CSV 共 3 行（1 行表头 + 2 行数据），且表头不重复。
- 判定：行数与首行内容匹配。

执行命令：
- F:/Anaconda/python.exe -m unittest -v tests/test_logger_module.py

## 三、实际测试及测试结果
实际结果：
- 共执行 2 个测试用例。
- 通过 2 个，失败 0 个，错误 0 个。
- 测试结论：通过。

关键输出摘录：
- Ran 2 tests in 0.014s
- OK

结论分析：
- logger 模块在字段写入、指标计算、追加写策略上行为正确。
- 该模块已具备支撑离线分析和实时日志落盘的基础可靠性。
- 建议后续补充异常路径测试（如磁盘不可写、路径不存在、并发写入）。
