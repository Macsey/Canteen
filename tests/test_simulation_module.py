import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from logger import DataLogger
from simulation import Simulation


class TestSimulationModule(unittest.TestCase):
    @patch("numpy.random.poisson", return_value=3)
    def test_generate_students_count(self, _mock_poisson):
        sim = Simulation(simulation_time=10, window_count=2)
        arrived = sim.generate_students(current_time=0, arrival_lambda=3.0)

        self.assertEqual(arrived, 3)
        self.assertEqual(sim.total_arrived, 3)
        self.assertEqual(sum(w.queue_length() for w in sim.windows), 3)

    @patch("numpy.random.poisson", return_value=2)
    @patch("random.gauss", return_value=2.0)
    def test_step_output_schema_and_time_progress(self, _mock_gauss, _mock_poisson):
        sim = Simulation(simulation_time=3, window_count=2, table_rows=2, table_cols=2)
        stats = sim.step()

        required_fields = {
            "time",
            "arrived_this_tick",
            "departed_this_tick",
            "total_arrived",
            "total_finished",
            "waiting_for_seat_count",
            "eating_count",
            "available_seats",
            "window_queue_lengths",
            "current_arrival_rate",
            "avg_service_time",
            "avg_eating_time",
        }
        self.assertTrue(required_fields.issubset(set(stats.keys())))
        self.assertEqual(stats["time"], 0)
        self.assertEqual(sim.current_time, 1)

    @patch("numpy.random.poisson", return_value=1)
    @patch("random.gauss", return_value=2.0)
    def test_run_produces_records_and_log(self, _mock_gauss, _mock_poisson):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "sim_test.csv"
            logger = DataLogger(file_path=str(log_path), total_seats=16, overwrite=True)
            sim = Simulation(simulation_time=5, window_count=2, table_rows=2, table_cols=2)
            records = sim.run(data_logger=logger)

            self.assertEqual(len(records), 5)
            self.assertTrue(log_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
