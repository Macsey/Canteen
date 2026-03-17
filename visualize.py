"""北京交通大学就餐仿真系统 - 可视化模块。

包含两类能力：
1. 离线分析：读取 simulation_log.csv，绘制历史曲线；
2. 实时分析：与 Simulation 实例联动，按 Tick 动态刷新图表。
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

import matplotlib.animation as animation
from matplotlib.colors import BoundaryNorm, ListedColormap
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Button, Slider, TextBox

from logger import DataLogger
from simulation import Simulation


class SimulationVisualizer:
    """仿真日志可视化器。"""

    def __init__(self, csv_path: str = "simulation_log.csv") -> None:
        self.csv_path = Path(csv_path)

        self.timestamps: List[int] = []
        self.total_queue_counts: List[int] = []
        self.empty_seat_rates: List[float] = []

        # 启用中文显示并避免负号显示异常
        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False

    def load_data(self) -> None:
        """从 CSV 文件加载数据。"""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"日志文件不存在: {self.csv_path}")

        self.timestamps.clear()
        self.total_queue_counts.clear()
        self.empty_seat_rates.clear()

        with self.csv_path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                self.timestamps.append(int(row["timestamp"]))
                self.total_queue_counts.append(int(row["total_queue_count"]))
                self.empty_seat_rates.append(float(row["empty_seat_rate"]))

    def plot_queue_trend(self) -> None:
        """绘制时间与总排队人数折线图。"""
        plt.figure(figsize=(10, 5))
        plt.plot(self.timestamps, self.total_queue_counts, color="#1f77b4", linewidth=2)
        plt.title("时间与总排队人数变化")
        plt.xlabel("时间 (Tick)")
        plt.ylabel("总排队人数")
        plt.grid(alpha=0.25)
        plt.tight_layout()

    def plot_empty_seat_rate_trend(self) -> None:
        """绘制时间与空座率折线图。"""
        plt.figure(figsize=(10, 5))
        plt.plot(self.timestamps, self.empty_seat_rates, color="#d62728", linewidth=2)
        plt.title("时间与空座率变化")
        plt.xlabel("时间 (Tick)")
        plt.ylabel("空座率")
        plt.ylim(0, 1)
        plt.grid(alpha=0.25)
        plt.tight_layout()

    def show(self) -> None:
        """加载数据并展示两张分析图。"""
        self.load_data()
        self.plot_queue_trend()
        self.plot_empty_seat_rate_trend()
        plt.show()

class RealTimeSimulationVisualizer:
    """实时仿真可视化器。

    图层说明：
    - 左上：各窗口当前排队规模（柱状图）。
    - 右上：餐桌占用热力图（每桌 0~4 人，用四色表示占用程度）。
    - 下方：人流实时表格（替代折线图）。
    """

    def __init__(
        self,
        simulation: Simulation,
        interval_ms: int = 300,
        simulation_factory: Optional[Callable[[], Simulation]] = None,
    ) -> None:
        self.simulation = simulation
        self.interval_ms = interval_ms
        self.simulation_factory = simulation_factory or (lambda: Simulation())
        self._paused = False
        self._logging_enabled = False
        self._live_logger: Optional[DataLogger] = None
        self._live_log_path = Path("simulation_log_live.csv")

        self.times: List[int] = []
        self.arrivals_per_tick: List[int] = []
        self.departures_per_tick: List[int] = []
        self.total_arrivals: List[int] = []
        self.total_queues: List[int] = []
        self.empty_rates: List[float] = []
        self.arrival_rates: List[float] = []
        self.service_speeds: List[float] = []
        self.eating_means: List[float] = []
        self.flow_table_rows: List[List[str]] = []

        self._flow_record_path = Path("realtime_flow_table_record.csv")
        self._flow_record_header = [
            "tick",
            "arrived_this_tick",
            "departed_this_tick",
            "in_restaurant_count",
            "total_queue_count",
            "empty_seat_rate",
            "service_speed_per_min",
            "avg_eating_time",
        ]

        self._syncing_text = False
        self._init_flow_record_file()

        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False

        self.fig = plt.figure(figsize=(14, 8))
        grid = self.fig.add_gridspec(2, 2, height_ratios=[1.0, 1.05])

        self.ax_queue = self.fig.add_subplot(grid[0, 0])
        self.ax_seat = self.fig.add_subplot(grid[0, 1])
        self.ax_flow = self.fig.add_subplot(grid[1, :])
        self._seat_colorbar = None

        self._setup_queue_panel()
        self._setup_seat_panel()
        self._setup_flow_panel()
        self._setup_control_panel()

        self.fig.suptitle("北京交通大学食堂实时仿真监控", fontsize=16)
        self.fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.31, wspace=0.23, hspace=0.34)

        self._step_iter = self.simulation.iter_steps()
        self._ani: animation.FuncAnimation | None = None

    def _setup_queue_panel(self) -> None:
        window_ids = [f"窗口{i}" for i in range(len(self.simulation.windows))]
        self.queue_bars = self.ax_queue.bar(window_ids, [0] * len(window_ids), color="#1f77b4", width=0.55)
        self.queue_texts = []
        for bar in self.queue_bars:
            text = self.ax_queue.text(
                bar.get_x() + bar.get_width() / 2,
                0.05,
                "0",
                ha="center",
                va="bottom",
                fontsize=9,
                color="#1f2937",
            )
            self.queue_texts.append(text)
        self.ax_queue.set_title("窗口排队情况")
        self.ax_queue.set_xlabel("窗口")
        self.ax_queue.set_ylabel("人数")
        self.ax_queue.grid(axis="y", alpha=0.25)

    def _setup_seat_panel(self) -> None:
        seats = np.array(self.simulation.table.seats, dtype=int)
        # 0 为白色（空桌），1~4 为四级占用颜色。
        cmap = ListedColormap(["#f7f7f7", "#b3e2cd", "#fdcdac", "#f4a582", "#d6604d"])
        norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)
        self.seat_img = self.ax_seat.imshow(
            seats,
            cmap=cmap,
            norm=norm,
            interpolation="nearest",
            aspect="auto",
        )
        self.ax_seat.set_title("桌位占用热力图（每桌最多4人）")
        self.ax_seat.set_xlabel("列")
        self.ax_seat.set_ylabel("行")
        self._seat_colorbar = self.fig.colorbar(self.seat_img, ax=self.ax_seat, fraction=0.046, pad=0.04)
        self._seat_colorbar.set_ticks([0, 1, 2, 3, 4])
        self._seat_colorbar.set_ticklabels(["0人", "1人", "2人", "3人", "4人"])

    def _setup_flow_panel(self) -> None:
        self.ax_flow.set_title("人流实时记录表（最近 10 条）")
        self.ax_flow.axis("off")
        self.flow_table = None

    def _init_flow_record_file(self) -> None:
        with self._flow_record_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(self._flow_record_header)

    def _append_flow_record(self, row: List[object]) -> None:
        with self._flow_record_path.open("a", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(row)

    def _setup_control_panel(self) -> None:
        """创建实时控制面板。"""
        btn_pause_ax = self.fig.add_axes([0.08, 0.03, 0.12, 0.05])
        btn_reset_ax = self.fig.add_axes([0.22, 0.03, 0.12, 0.05])

        # 右下角参数区改为纵向 4 行，避免标签和输入框相互遮挡。
        speed_slider_ax = self.fig.add_axes([0.66, 0.12, 0.24, 0.025])
        speed_box_ax = self.fig.add_axes([0.91, 0.12, 0.07, 0.025])
        arrival_slider_ax = self.fig.add_axes([0.66, 0.085, 0.24, 0.025])
        arrival_box_ax = self.fig.add_axes([0.91, 0.085, 0.07, 0.025])
        service_slider_ax = self.fig.add_axes([0.66, 0.05, 0.24, 0.025])
        service_box_ax = self.fig.add_axes([0.91, 0.05, 0.07, 0.025])
        eating_slider_ax = self.fig.add_axes([0.66, 0.015, 0.24, 0.025])
        eating_box_ax = self.fig.add_axes([0.91, 0.015, 0.07, 0.025])

        self.pause_button = Button(btn_pause_ax, "暂停")
        self.reset_button = Button(btn_reset_ax, "重置")

        self.speed_slider = Slider(
            speed_slider_ax,
            "速度",
            valmin=50,
            valmax=1000,
            valinit=float(self.interval_ms),
            valstep=10,
        )
        self.arrival_slider = Slider(
            arrival_slider_ax,
            "到达率",
            valmin=1.0,
            valmax=50.0,
            valinit=float(self.simulation.arrival_rate),
            valstep=0.5,
        )
        service_speed_init = self._service_speed_from_time(self.simulation.avg_service_time)
        self.service_slider = Slider(
            service_slider_ax,
            "打饭速度",
            valmin=5.0,
            valmax=60.0,
            valinit=float(service_speed_init),
            valstep=0.5,
        )
        self.eating_slider = Slider(
            eating_slider_ax,
            "就餐均时",
            valmin=5.0,
            valmax=40.0,
            valinit=float(self.simulation.avg_eating_time),
            valstep=0.5,
        )

        self.speed_box = TextBox(speed_box_ax, "", initial=f"{self.interval_ms:.0f}")
        self.arrival_box = TextBox(arrival_box_ax, "", initial=f"{self.simulation.arrival_rate:.1f}")
        self.service_box = TextBox(service_box_ax, "", initial=f"{service_speed_init:.1f}")
        self.eating_box = TextBox(eating_box_ax, "", initial=f"{self.simulation.avg_eating_time:.1f}")

        # 使用右侧输入框作为唯一数值显示，避免与 Slider 默认值文本重叠。
        self.speed_slider.valtext.set_visible(False)
        self.arrival_slider.valtext.set_visible(False)
        self.service_slider.valtext.set_visible(False)
        self.eating_slider.valtext.set_visible(False)

        self.pause_button.on_clicked(self._on_pause_clicked)
        self.reset_button.on_clicked(self._on_reset_clicked)
        self.speed_slider.on_changed(self._on_speed_changed)
        self.arrival_slider.on_changed(self._on_arrival_rate_changed)
        self.service_slider.on_changed(self._on_service_speed_changed)
        self.eating_slider.on_changed(self._on_eating_time_changed)

        self.speed_box.on_submit(self._on_speed_text_submit)
        self.arrival_box.on_submit(self._on_arrival_text_submit)
        self.service_box.on_submit(self._on_service_text_submit)
        self.eating_box.on_submit(self._on_eating_text_submit)

    @staticmethod
    def _service_speed_from_time(avg_service_time: float) -> float:
        service_time = max(0.1, float(avg_service_time))
        return 60.0 / service_time

    @staticmethod
    def _service_time_from_speed(service_speed: float) -> float:
        speed = max(0.1, float(service_speed))
        return 60.0 / speed

    @staticmethod
    def _clamp(value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    def _update_textbox(self, box: TextBox, text: str) -> None:
        self._syncing_text = True
        box.set_val(text)
        self._syncing_text = False

    def _parse_text_value(self, text: str) -> Optional[float]:
        try:
            return float(str(text).strip())
        except (TypeError, ValueError):
            return None

    def _on_pause_clicked(self, _event) -> None:
        self._paused = not self._paused
        self.pause_button.label.set_text("继续" if self._paused else "暂停")

    def _on_reset_clicked(self, _event) -> None:
        """重置仿真状态并清空历史曲线。"""
        self.simulation = self.simulation_factory()
        self.simulation.arrival_rate = float(self.arrival_slider.val)
        self.simulation.avg_service_time = self._service_time_from_speed(float(self.service_slider.val))
        self.simulation.avg_eating_time = float(self.eating_slider.val)
        self._step_iter = self.simulation.iter_steps()
        self._paused = False
        self.pause_button.label.set_text("暂停")

        self.times.clear()
        self.arrivals_per_tick.clear()
        self.departures_per_tick.clear()
        self.total_arrivals.clear()
        self.total_queues.clear()
        self.empty_rates.clear()
        self.arrival_rates.clear()
        self.service_speeds.clear()
        self.eating_means.clear()
        self.flow_table_rows.clear()
        self._init_flow_record_file()

        # 保留现有图层对象，仅重置可变数据，避免频繁销毁重建带来的兼容问题。
        for idx, bar in enumerate(self.queue_bars):
            bar.set_height(0)
            self.queue_texts[idx].set_text("0")
            self.queue_texts[idx].set_y(0.05)
        self.ax_queue.set_ylim(0, 2)

        seats = np.array(self.simulation.table.seats, dtype=int)
        self.seat_img.set_data(seats)

        self.ax_flow.clear()
        self._setup_flow_panel()

        self.fig.suptitle("北京交通大学食堂实时仿真监控", fontsize=16)

        # 仿真结束后 event_source 会被 stop；重置时需显式重启动画计时器。
        if self._ani is not None:
            self._ani.event_source.start()

    def _on_speed_changed(self, value: float) -> None:
        self.interval_ms = int(value)
        self._update_textbox(self.speed_box, f"{self.interval_ms:.0f}")
        if self._ani is not None:
            self._ani.event_source.interval = self.interval_ms

    def _on_arrival_rate_changed(self, value: float) -> None:
        self.simulation.arrival_rate = float(value)
        self._update_textbox(self.arrival_box, f"{self.simulation.arrival_rate:.1f}")

    def _on_service_speed_changed(self, value: float) -> None:
        self.simulation.avg_service_time = self._service_time_from_speed(float(value))
        self._update_textbox(self.service_box, f"{float(value):.1f}")

    def _on_eating_time_changed(self, value: float) -> None:
        self.simulation.avg_eating_time = float(value)
        self._update_textbox(self.eating_box, f"{self.simulation.avg_eating_time:.1f}")

    def _on_speed_text_submit(self, text: str) -> None:
        if self._syncing_text:
            return
        parsed = self._parse_text_value(text)
        if parsed is None:
            self._update_textbox(self.speed_box, f"{self.speed_slider.val:.0f}")
            return
        clamped = self._clamp(parsed, self.speed_slider.valmin, self.speed_slider.valmax)
        self.speed_slider.set_val(clamped)

    def _on_arrival_text_submit(self, text: str) -> None:
        if self._syncing_text:
            return
        parsed = self._parse_text_value(text)
        if parsed is None:
            self._update_textbox(self.arrival_box, f"{self.arrival_slider.val:.1f}")
            return
        clamped = self._clamp(parsed, self.arrival_slider.valmin, self.arrival_slider.valmax)
        self.arrival_slider.set_val(clamped)

    def _on_service_text_submit(self, text: str) -> None:
        if self._syncing_text:
            return
        parsed = self._parse_text_value(text)
        if parsed is None:
            self._update_textbox(self.service_box, f"{self.service_slider.val:.1f}")
            return
        clamped = self._clamp(parsed, self.service_slider.valmin, self.service_slider.valmax)
        self.service_slider.set_val(clamped)

    def _on_eating_text_submit(self, text: str) -> None:
        if self._syncing_text:
            return
        parsed = self._parse_text_value(text)
        if parsed is None:
            self._update_textbox(self.eating_box, f"{self.eating_slider.val:.1f}")
            return
        clamped = self._clamp(parsed, self.eating_slider.valmin, self.eating_slider.valmax)
        self.eating_slider.set_val(clamped)

    def _on_save_clicked(self, _event) -> None:
        """保存当前实时监控画面到 PNG。"""
        current_tick = self.times[-1] if self.times else 0
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"realtime_snapshot_t{current_tick}_{stamp}.png")
        self.fig.savefig(output, dpi=150)

    def _on_log_clicked(self, _event) -> None:
        """切换实时日志记录状态。"""
        self._logging_enabled = not self._logging_enabled
        if self._logging_enabled:
            if self._live_logger is None:
                self._live_logger = DataLogger(
                    file_path=str(self._live_log_path),
                    total_seats=(
                        self.simulation.table.rows
                        * self.simulation.table.cols
                        * self.simulation.table.capacity_per_unit
                    ),
                    overwrite=False,
                )
                self._live_logger.open()
            self.log_button.label.set_text("日志:开")
        else:
            self.log_button.label.set_text("日志:关")

    def _on_close(self, _event) -> None:
        """关闭窗口时回收文件句柄。"""
        if self._live_logger is not None:
            self._live_logger.close()
            self._live_logger = None

    def _update_queue_panel(self, queue_lengths: List[int]) -> None:
        max_queue = 1
        if queue_lengths:
            max_queue = max(max(queue_lengths), 1)

        for bar, value in zip(self.queue_bars, queue_lengths):
            bar.set_height(value)
        for idx, value in enumerate(queue_lengths):
            self.queue_texts[idx].set_text(str(value))
            self.queue_texts[idx].set_y(value + 0.05)
        self.ax_queue.set_ylim(0, max_queue + 2)

    def _update_seat_panel(self) -> None:
        seats = np.array(self.simulation.table.seats, dtype=int)
        self.seat_img.set_data(seats)

    def _update_flow_panel(self) -> None:
        if not self.flow_table_rows:
            return

        self.ax_flow.clear()
        self.ax_flow.set_title("人流实时记录表（最近 10 条）")
        self.ax_flow.axis("off")

        max_rows = 10
        rows = self.flow_table_rows[-max_rows:]
        self.flow_table = self.ax_flow.table(
            cellText=rows,
            colLabels=["Tick", "到达", "离开", "餐厅总人数", "排队总人数", "空座率", "打饭速度(人/分)", "用餐均时"],
            loc="center",
            cellLoc="center",
        )
        self.flow_table.auto_set_font_size(False)
        self.flow_table.set_fontsize(9)
        self.flow_table.scale(1.0, 1.15)

    def _update(self, _frame_index: int):
        if self._paused:
            return self.queue_bars

        try:
            stats = next(self._step_iter)
        except StopIteration:
            if self._ani is not None:
                self._ani.event_source.stop()
            return self.queue_bars

        current_time = int(stats["time"])
        queue_lengths = list(stats["window_queue_lengths"])
        arrived_this_tick = int(stats["arrived_this_tick"])
        departed_this_tick = int(stats.get("departed_this_tick", 0))
        total_arrived = int(stats["total_arrived"])
        available_seats = int(stats["available_seats"])
        total_seats = (
            self.simulation.table.rows
            * self.simulation.table.cols
            * self.simulation.table.capacity_per_unit
        )

        self.times.append(current_time)
        self.arrivals_per_tick.append(arrived_this_tick)
        self.departures_per_tick.append(departed_this_tick)
        self.total_arrivals.append(total_arrived)
        self.arrival_rates.append(float(stats["current_arrival_rate"]))
        service_speed = self._service_speed_from_time(float(stats["avg_service_time"]))
        self.service_speeds.append(service_speed)
        avg_eating_time = float(stats["avg_eating_time"])
        self.eating_means.append(avg_eating_time)
        total_finished = int(stats["total_finished"])

        total_queue = sum(queue_lengths) + int(stats["waiting_for_seat_count"])
        empty_rate = 0.0 if total_seats == 0 else available_seats / total_seats
        in_restaurant_count = max(0, total_arrived - total_finished)
        self.total_queues.append(total_queue)
        self.empty_rates.append(empty_rate)

        display_row = [
            str(current_time),
            str(arrived_this_tick),
            str(departed_this_tick),
            str(in_restaurant_count),
            str(total_queue),
            f"{empty_rate:.1%}",
            f"{service_speed:.1f}",
            f"{avg_eating_time:.1f}",
        ]
        self.flow_table_rows.append(display_row)
        self._append_flow_record(
            [
                current_time,
                arrived_this_tick,
                departed_this_tick,
                in_restaurant_count,
                total_queue,
                round(empty_rate, 6),
                round(service_speed, 3),
                round(avg_eating_time, 3),
            ]
        )

        self._update_queue_panel(queue_lengths)
        self._update_seat_panel()
        self._update_flow_panel()

        if self._logging_enabled and self._live_logger is not None:
            self._live_logger.log_tick(stats)

        self.fig.suptitle(
            f"北京交通大学食堂实时仿真监控 | Tick={current_time} | 到达={arrived_this_tick} | 离开={departed_this_tick} | 总排队={total_queue} | 空座率={empty_rate:.2%}",
            fontsize=14,
        )
        return self.queue_bars

    def run(self) -> None:
        """启动实时动画窗口。"""
        self.fig.canvas.mpl_connect("close_event", self._on_close)
        self._ani = animation.FuncAnimation(
            self.fig,
            self._update,
            interval=self.interval_ms,
            blit=False,
            repeat=False,
        )
        plt.show()


def run_realtime_demo(interval_ms: int = 300) -> None:
    """快速启动实时演示。"""
    visualizer = RealTimeSimulationVisualizer(
        simulation=Simulation(),
        interval_ms=interval_ms,
        simulation_factory=lambda: Simulation(),
    )
    visualizer.run()


if __name__ == "__main__":
    # 默认启动实时模式；若只看离线曲线可改为 SimulationVisualizer("simulation_log.csv").show()
    run_realtime_demo(interval_ms=300)
