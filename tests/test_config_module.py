import unittest

import config


class TestConfigModule(unittest.TestCase):
    def test_basic_numeric_constraints(self):
        self.assertGreater(config.SIMULATION_TIME, 0)
        self.assertGreater(config.WINDOW_COUNT, 0)
        self.assertGreater(config.TABLE_ROWS, 0)
        self.assertGreater(config.TABLE_COLS, 0)
        self.assertGreater(config.TABLE_CAPACITY_PER_UNIT, 0)
        self.assertGreater(config.ARRIVAL_RATE, 0)
        self.assertGreater(config.AVG_SERVICE_TIME, 0)
        self.assertGreater(config.AVG_EATING_TIME, 0)

    def test_peak_offpeak_factors_are_positive(self):
        self.assertGreater(config.ARRIVAL_PEAK_FACTOR, 0)
        self.assertGreater(config.ARRIVAL_OFFPEAK_FACTOR, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
