import io
import unittest
from contextlib import redirect_stdout

import hello_canteen


class TestHelloCanteenModule(unittest.TestCase):
    def test_main_prints_expected_messages(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            hello_canteen.main()
        output = buf.getvalue()

        self.assertIn("Hello Canteen! 环境可用", output)
        self.assertIn("共运行", output)
        self.assertIn("最终累计到达人数", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
