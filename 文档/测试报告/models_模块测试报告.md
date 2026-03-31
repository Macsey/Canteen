# models 模块测试报告

## 一、测试什么
测试对象：Student、Window、Table 三个核心实体。

测试目标：
- 函数输入输出正确性：方法调用后的返回值是否符合定义。
- 模块逻辑正确性：状态迁移、排队服务、座位占用与释放逻辑是否正确。

覆盖项：
- Student.start_service / start_eating / update_state_on_tick。
- Window.enqueue / handle_service_tick / queue_length。
- Table.occupy_seat / release_seat / available_count。

## 二、如何测试
测试方式：自动化测试（unittest）。

测试程序：tests/test_models_module.py

测试用例设计：
1. test_state_transition_service_to_waiting_seat
- 输入：学生服务时长 2 Tick。
- 预期：第一次 update 无完成事件；第二次返回 service_finished，状态转为 waiting_seat。
- 判定：事件值与状态字段同时匹配。

2. test_state_transition_eating_to_finished
- 输入：学生就餐时长 2 Tick。
- 预期：第二次 update 返回 eating_finished，状态转为 finished。
- 判定：事件值与状态字段匹配。

3. test_window_queue_and_service
- 输入：窗口入队两个学生，服务采样固定为 1 Tick。
- 预期：单次服务推进后完成第 1 人，累计服务数 +1，队列规模减少。
- 判定：finished.id=1，total_served=1，queue_length=1。

4. test_occupy_and_release
- 输入：1x1 桌位，每桌容量 2。
- 预期：前两次占座成功，第三次失败；释放后可用座位 +1。
- 判定：seat1/seat2 非空，seat3 为空，available_count 变化正确。

5. test_release_invalid_position
- 输入：非法座位坐标 (2,2)。
- 预期：释放失败。
- 判定：返回 False。

执行命令：
- F:/Anaconda/python.exe -m unittest -v tests/test_models_module.py

## 三、实际测试及测试结果
实际结果：
- 共执行 5 个测试用例。
- 通过 5 个，失败 0 个，错误 0 个。
- 测试结论：通过。

关键输出摘录：
- Ran 5 tests in 0.001s
- OK

结论分析：
- 核心实体状态流转与关键行为符合预期。
- 当前测试已覆盖主路径和部分边界场景（非法释放）。
- 建议后续补充随机分配稳定性与高并发排队压力场景测试。
