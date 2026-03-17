"""北京交通大学就餐仿真系统 - 全局配置模块。

本文件集中管理仿真所需的超参数，方便统一调优与实验对比。
你可以根据不同场景（早高峰、午高峰、晚高峰）复制一份配置进行修改。
"""

# 仿真总时长（单位由主程序自行约定，建议使用“分钟”）
SIMULATION_TIME: int = 180

# 食堂开放窗口数量
WINDOW_COUNT: int = 8

# 餐桌矩阵大小（行、列）
TABLE_ROWS: int = 12
TABLE_COLS: int = 10

# 每张桌子的固定容量（每桌最多可坐 4 人）
TABLE_CAPACITY_PER_UNIT: int = 4

# 到达率：每 Tick 进入食堂的平均人数（泊松分布参数 lambda）
# 说明：该默认值与窗口服务能力匹配，可观察到排队在峰谷间的上升与回落。
ARRIVAL_RATE: float = 1.8

# 人流峰谷因子（用于构造更接近现实的到达率曲线）
# - 早段：基准流量
# - 高峰：基准流量 * ARRIVAL_PEAK_FACTOR
# - 回落：基准流量 * ARRIVAL_OFFPEAK_FACTOR
ARRIVAL_PEAK_FACTOR: float = 1.45
ARRIVAL_OFFPEAK_FACTOR: float = 0.75

# 打饭服务时长（正态分布参数）
AVG_SERVICE_TIME: float = 2.8
STD_SERVICE_TIME: float = 0.7

# 就餐时长（正态分布参数）
AVG_EATING_TIME: float = 16.0
STD_EATING_TIME: float = 4.0
