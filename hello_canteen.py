from simulation import Simulation


def main() -> None:
    sim = Simulation(simulation_time=5)
    records = sim.run()
    print("Hello Canteen! 环境可用")
    print(f"共运行 {len(records)} 个 Tick")
    print(f"最终累计到达人数: {records[-1]['total_arrived'] if records else 0}")


if __name__ == "__main__":
    main()
