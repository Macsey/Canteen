# 联调测试报告

## 1. 测试目的

本次联调测试用于验证“北京交通大学就餐仿真系统”中 `Student`、`Window`、`Table`、`Simulation`、`SimulationStats`、`DataLogger` 等模块之间的接口连通性、状态流转正确性和系统端到端闭环能力。测试重点不是单个函数是否孤立可用，而是学生从到达、排队、打饭、等座、就餐、离开，到统计数据生成和 CSV 日志写入的完整业务链路是否稳定。

## 2. 测试环境

| 项目 | 内容 |
| --- | --- |
| 操作系统 | Windows 11 10.0.26200 |
| Python 版本 | Python 3.13.5 |
| pytest 版本 | pytest 8.3.4 |
| numpy 版本 | numpy 2.3.5 |
| 项目运行方式 | 在仓库根目录执行 `pytest tests/integration -v` |
| 随机性控制 | 使用 `monkeypatch` 固定 `numpy.random.poisson`，并在关键场景中固定 `Simulation._sample_service_time` 与 `Simulation._sample_eating_time` |

## 3. 被测模块

| 模块名称 | 核心类/函数 | 输入 | 输出 | 测试重点 |
| --- | --- | --- | --- | --- |
| `models.Student` | `start_service`、`start_eating`、`update_state_on_tick` | 当前 tick、服务时长、就餐时长、座位坐标 | 学生状态、剩余时间、完成事件 | `waiting`、`serving`、`waiting_seat`、`eating`、`finished` 状态流转 |
| `models.Window` | `enqueue`、`handle_service_tick`、`queue_length` | 学生对象、当前 tick、服务时间采样器 | 完成服务的学生或 `None`、队列长度 | 队列接入、服务启动、服务完成、累计服务人数 |
| `models.Table` | `occupy_seat`、`release_seat`、`available_count` | 座位偏好、座位坐标 | 座位坐标、释放结果、空座数量 | 座位占用、释放、重复释放、非法坐标 |
| `simulation.Simulation` | `generate_students`、`update_windows`、`update_tables`、`step`、`run` | 仿真配置、当前 tick、可选日志器 | 每 tick 统计字典、完整 records | 模块编排、等座队列、就餐完成、端到端闭环 |
| `simulation.SimulationStats` | `to_dict` | 单 tick 统计字段 | 稳定字段结构的字典 | 统计字段完整性、字段类型、累计值关系 |
| `logger.DataLogger` | `open`、`log_tick`、`close`、上下文管理器 | `Simulation.step()` 统计字典 | CSV 文件与行数据 | CSV 表头、日志行数、队列和空座率字段映射 |

## 4. 接口联调测试设计

| 测试编号 | 测试名称 | 上游模块 | 下游模块 | 测试目标 | 预期结果 | 测试文件 | 测试函数 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IF-01 | Student 与 Window 服务流 | `Student` | `Window` | 学生进入窗口队列并完成服务 | 学生变为 `waiting_seat`，窗口空闲，`total_served=1` | `tests/integration/test_interface_integration.py` | `test_student_window_service_flow` |
| IF-02 | Window 完成学生进入 Table | `Window` / `Student` | `Table` | 完成打饭的学生被安排座位并开始就餐 | 学生变为 `eating`，空座数减少 | 同上 | `test_finished_service_student_can_be_allocated_to_table` |
| IF-03 | Table 座位释放 | `Student` | `Table` | 就餐结束后的座位释放接口正确 | 首次释放成功，重复释放和非法坐标失败 | 同上 | `test_table_release_seat_handles_success_duplicate_and_invalid_positions` |
| IF-04 | Simulation 生成学生进入 Window | `Simulation.generate_students` | `Window` | 到达学生自动分配到最短窗口 | 到达数正确，队列总数正确，窗口负载均衡 | 同上 | `test_simulation_generate_students_balances_window_queues` |
| IF-05A | Window 完成后有座入座 | `Simulation.update_windows` | `Table` / `Student` | 完成服务学生进入就餐区 | `eating_students` 增加，等座队列为空 | 同上 | `test_simulation_update_windows_allocates_finished_student_to_table` |
| IF-05B | Window 完成后无座等座 | `Simulation.update_windows` | `waiting_for_seat` | 无座位时完成服务学生进入等座队列 | 学生保持 `waiting_seat`，等座队列增加 | 同上 | `test_simulation_update_windows_moves_finished_student_to_waiting_queue_when_no_seat` |
| IF-06 | Table 离座与等座重分配 | `Simulation.update_tables` | `Table` / `Student` | 就餐完成释放座位，并为等座学生入座 | `total_finished` 增加，等座学生进入 `eating` | 同上 | `test_simulation_update_tables_releases_finished_seat_and_reallocates_waiting_student` |
| IF-07 | step 统计结构 | `Simulation.step` | `SimulationStats` | 单 tick 整合返回稳定统计字段 | 必需字段存在，类型和累计关系正确 | 同上 | `test_simulation_step_returns_stable_stats_schema` |
| IF-08 | run 与 DataLogger | `Simulation.run` | `DataLogger` | 完整运行写入 CSV | records 长度正确，CSV 表头和行数正确 | 同上 | `test_simulation_run_writes_csv_through_data_logger` |

## 5. 系统联调测试设计

| 测试编号 | 场景名称 | 输入配置 | 随机到达设置 | 预期现象 | 关键断言 | artifact 文件 |
| --- | --- | --- | --- | --- | --- | --- |
| SYS-01 | 正常低流量就餐闭环 | 8 tick、1 窗口、2 座位、服务 1、就餐 2 | `[1,0,0,0,0,0,0,0]` | 学生顺利完成到达到离开 | `total_arrived>=1`、`total_finished>=1`、最终空座恢复 | `tests/reports/artifacts/normal_flow_case.json` |
| SYS-02 | 窗口排队压力 | 3 tick、2 窗口、大容量餐桌、服务 3 | `[8,0,0]` | 窗口形成排队且负载相对均衡 | `total_arrived==8`、队列总数曾大于 0、人数守恒 | `tests/reports/artifacts/window_queue_pressure_case.json` |
| SYS-03 | 座位不足导致等座 | 4 tick、2 窗口、1 座位、服务 1、就餐 5 | `[3,0,0,0]` | 有学生就餐且后续学生等待座位 | 等座数曾大于 0，空座不为负，就餐数不超容量 | `tests/reports/artifacts/seat_shortage_case.json` |
| SYS-04 | 等座学生重新入座 | 8 tick、1 窗口、1 座位、服务 1、就餐 2 | `[2,0,0,0,0,0,0,0]` | 等座队列先上升后下降 | 等座数曾大于 0，后续下降，座位数始终合法 | `tests/reports/artifacts/waiting_reallocation_case.json` |
| SYS-05 | 完整日志记录 | 5 tick、2 窗口、16 座位、服务 1、就餐 2 | `[2,1,0,0,0]` | records 与 CSV 均可用于报告分析 | CSV 数据行数等于 tick 数，空座率在 `[0,1]`，累计进入人数单调 | `tests/reports/artifacts/logger_case.json` |

## 6. 测试结果

当前新增联调测试已通过命令 `pytest tests/integration -v` 执行，结果为 `14 passed in 0.27s`。其中接口联调测试 9 个，系统联调测试 5 个。系统用例运行时会在 `tests/reports/artifacts/` 下写入 JSON 产物，记录输入配置、每 tick records、最终状态、关键观察和通过情况。

关键日志摘要包括：

- `DataLogger` CSV 表头为 `timestamp,total_entered,total_queue_count,empty_seat_rate`。
- `Simulation.step()` 返回的统计字段包含到达、离开、累计人数、等座人数、就餐人数、空座数、窗口队列长度、当前到达率和平均时长。
- 系统用例中的人数守恒检查使用窗口队列人数、等座人数、就餐人数和已完成人数之和对比累计到达人数。

## 7. 典型联调链路分析

链路一：学生正常就餐闭环

`Simulation.generate_students()` 根据固定的泊松采样生成 `Student`，并通过 `_choose_least_loaded_window()` 进入 `Window` 队列。`Window.handle_service_tick()` 从队列取出学生，调用 `Student.start_service()` 后推进一个 tick；服务完成时 `Student.update_state_on_tick()` 将状态转为 `waiting_seat` 并返回给 `Simulation.update_windows()`。随后 `Simulation._try_allocate_seat()` 调用 `Table.occupy_seat()` 获取座位，并调用 `Student.start_eating()` 将学生转为 `eating`。当 `Simulation.update_tables()` 判断 `current_time >= eating_start_time + eating_duration` 时，调用 `Table.release_seat()` 释放座位，将学生置为 `finished`，并通过 `SimulationStats.to_dict()` 输出统计快照。

链路二：座位不足与等座重分配

多个学生到达后被分配到窗口队列；窗口服务完成的学生会优先尝试入座。若 `Table.occupy_seat()` 返回 `None`，`Simulation.update_windows()` 将学生放入 `waiting_for_seat` 队列，学生状态保持 `waiting_seat`。当正在就餐的学生达到离开时间，`Simulation.update_tables()` 释放其座位，并在 `while self.waiting_for_seat and self.table.available_count() > 0` 循环中按 FIFO 为等座学生重新调用 `_try_allocate_seat()`。测试验证了等座队列先出现、后下降，且空座数始终处于合法区间。

## 8. 发现的问题

- 随机性较强，联调测试必须固定 `numpy.random.poisson`，否则到达人数会导致断言不稳定。
- `Table.occupy_seat()` 内部使用 `random.choice`，在多座位场景下座位坐标可能变化；本次测试主要通过容量和状态断言规避坐标随机性，必要时可进一步固定 `random.seed` 或 monkeypatch。
- `Simulation.update_tables()` 使用 `eating_start_time + eating_duration` 判定就餐结束，而 `Student.update_state_on_tick()` 也能推进 `eating` 状态。当前仿真主流程采用前者，测试按主流程行为验证。
- `DataLogger` 只记录 `timestamp`、`total_entered`、`total_queue_count`、`empty_seat_rate` 四个字段，不记录完整 `records`；完整 records 由 `Simulation.run()` 返回或由系统测试写入 JSON artifact。
- 暂未发现阻塞性问题。

## 9. 修改建议

- 增加统一的 `Simulation` state snapshot，用于调试、可视化和人数守恒检查。
- 增加学生守恒检查，例如到达总人数等于窗口中、等座中、就餐中和已完成的学生总数。
- 增加随机种子配置，将泊松到达、服务时长、就餐时长、座位选择统一纳入可复现实验配置。
- 增加场景配置文件，例如 YAML/JSON，用于批量运行低流量、高流量、座位不足等实验。
- 增加 CSV 与 JSON 双格式日志，使统计分析和可视化回放都能直接消费。
- 增加可视化回放接口，将每 tick 的窗口、餐桌、学生状态快照持久化。
- 增加边界条件测试，例如 0 个窗口、0 个座位、仿真时间为 0、极大到达量、极长就餐时间等。

## 10. 结论

从新增联调测试设计看，当前系统具备基本的模块连通能力和端到端就餐仿真闭环能力：学生可以到达、排队、接受服务、入座、就餐、离开，`Simulation` 能输出每 tick 统计数据，`DataLogger` 能写入 CSV 日志。该能力可以支撑课程实训报告、实验数据分析和后续可视化展示；若要用于更复杂实验，建议优先补充统一状态快照、随机种子配置和更完整的日志结构。
