import csv
import tempfile
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from simulation import Simulation
from visualize import RealTimeSimulationVisualizer, SimulationVisualizer


class TestSimulationVisualizer(unittest.TestCase):
    def test_load_data_from_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "viz_test.csv"
            with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "total_entered", "total_queue_count", "empty_seat_rate"])
                writer.writerow([0, 1, 2, 0.75])
                writer.writerow([1, 2, 3, 0.50])

            visualizer = SimulationVisualizer(csv_path=str(csv_path))
            visualizer.load_data()

            self.assertEqual(visualizer.timestamps, [0, 1])
            self.assertEqual(visualizer.total_queue_counts, [2, 3])
            self.assertEqual(visualizer.empty_seat_rates, [0.75, 0.5])


class TestRealTimeSimulationVisualizer(unittest.TestCase):
    def test_helper_functions(self):
        speed = RealTimeSimulationVisualizer._service_speed_from_time(2.0)
        service_time = RealTimeSimulationVisualizer._service_time_from_speed(speed)
        clamped = RealTimeSimulationVisualizer._clamp(120, 0, 100)

        self.assertAlmostEqual(speed, 30.0)
        self.assertAlmostEqual(service_time, 2.0)
        self.assertEqual(clamped, 100)

    def test_construct_visualizer_without_runtime_error(self):
        sim = Simulation(simulation_time=2, window_count=2, table_rows=2, table_cols=2)
        visualizer = RealTimeSimulationVisualizer(simulation=sim, interval_ms=300)
        self.assertIsNotNone(visualizer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
