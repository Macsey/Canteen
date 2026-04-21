# models 与 simulation 测试模块报告

## 1. 测试什么？

本次测试对象为 `models.py` 与 `simulation.py` 两个核心模块，重点验证以下三类正确性：

- 函数输入输出正确性：给定确定输入时，返回值与状态变化是否符合预期。
- 模块输入输出正确性：模块对外接口（如 `step()`、`run()`）输出字段是否完整、数量是否正确。
- 函数/模块逻辑正确性：学生状态流转、窗口排队服务、座位占用释放、仿真时间推进与日志联动是否正确。

覆盖的核心功能包括：

- `models.Student`：`start_service`、`start_eating`、`update_state_on_tick`
- `models.Window`：`enqueue`、`handle_service_tick`、`queue_length`
- `models.Table`：`occupy_seat`、`release_seat`、`available_count`
- `simulation.Simulation`：`generate_students`、`step`、`run`

## 2. 如何测试？

测试方式采用自动化单元测试（`unittest` + `mock`），对应文件：

- `tests/test_models_module.py`
- `tests/test_simulation_module.py`

执行命令：

```bash
python -m unittest tests.test_models_module tests.test_simulation_module -v
```

关键用例设计如下（输入 / 预期 / 判定）：

1. `Student` 服务阶段状态流转  
输入：服务时长 `2 tick`。  
预期：第一次更新无完成事件，第二次返回 `service_finished`，状态变为 `waiting_seat`。  
判定：事件值与 `status` 字段同时匹配。

2. `Student` 就餐阶段状态流转  
输入：就餐时长 `2 tick`。  
预期：第二次更新返回 `eating_finished`，状态变为 `finished`。  
判定：事件值与状态字段匹配。

3. `Window` 排队与服务逻辑  
输入：2 名学生入队，服务采样固定为 `1 tick`。  
预期：单步服务后第 1 名学生完成，`total_served=1`，队列长度减少。  
判定：`finished.id=1`、`total_served=1`、`queue_length=1`。

4. `Table` 占座与释放逻辑  
输入：`1x1` 餐桌，容量 `2`。  
预期：前两次占座成功，第三次失败；释放后可用座位增加。  
判定：`seat1/seat2` 非空、`seat3` 为空、`available_count` 变化正确。

5. `Table` 非法释放边界  
输入：非法坐标 `(2,2)`。  
预期：释放失败。  
判定：返回 `False`。

6. `Simulation.generate_students` 计数正确性  
输入：mock `numpy.random.poisson=3`。  
预期：本 tick 到达 `3` 人，总到达 `3`，各窗口队列总和 `3`。  
判定：三项计数一致。

7. `Simulation.step` 输出结构与时间推进  
输入：mock `poisson=2`，mock `random.gauss=2.0`。  
预期：返回结果包含 12 个关键字段，`time=0` 且 `current_time` 推进到 `1`。  
判定：字段集合包含关系成立且时间值正确。

8. `Simulation.run` 全流程与日志联动  
输入：`simulation_time=5`，临时日志路径，mock `poisson=1`，mock `gauss=2.0`。  
预期：返回 5 条记录并生成 CSV 日志文件。  
判定：`len(records)=5` 且日志文件存在。

## 3. 实际测试及测试结果是什么？

实际执行时间：`2026-04-21`  
实际执行命令：

```bash
python -m unittest tests.test_models_module tests.test_simulation_module -v
```

实际结果摘要：

- 总计执行：`8` 个测试用例
- 通过：`8`
- 失败：`0`
- 错误：`0`
- 最终结论：`OK`

关键输出：

```text
Ran 8 tests in 0.030s
OK
```

结论：`models` 与 `simulation` 模块在当前测试范围内功能正确，核心输入输出与主要业务逻辑均符合预期，可支撑后续集成与可视化联调。
