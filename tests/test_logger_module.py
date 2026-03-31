import csv
import tempfile
import unittest
from pathlib import Path

from logger import DataLogger


class TestLoggerModule(unittest.TestCase):
    def test_logger_header_and_single_row(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "logger_test.csv"
            logger = DataLogger(file_path=str(csv_path), total_seats=20, overwrite=True)

            state = {
                "time": 1,
                "total_arrived": 10,
                "window_queue_lengths": [2, 1, 0],
                "waiting_for_seat_count": 3,
                "available_seats": 10,
            }

            with logger:
                logger.log_tick(state)

            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))

            self.assertEqual(rows[0], DataLogger.HEADER)
            self.assertEqual(rows[1], ["1", "10", "6", "0.5"])

    def test_logger_append_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "logger_append.csv"

            logger1 = DataLogger(file_path=str(csv_path), total_seats=10, overwrite=True)
            with logger1:
                logger1.log_tick(
                    {
                        "time": 0,
                        "total_arrived": 1,
                        "window_queue_lengths": [0],
                        "waiting_for_seat_count": 0,
                        "available_seats": 9,
                    }
                )

            logger2 = DataLogger(file_path=str(csv_path), total_seats=10, overwrite=False)
            with logger2:
                logger2.log_tick(
                    {
                        "time": 1,
                        "total_arrived": 2,
                        "window_queue_lengths": [1],
                        "waiting_for_seat_count": 0,
                        "available_seats": 8,
                    }
                )

            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))

            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0], DataLogger.HEADER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
