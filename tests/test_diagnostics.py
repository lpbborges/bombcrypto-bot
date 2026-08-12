from config import BotConfig
import unittest
from config import BotConfig
from unittest.mock import patch

from modules.diagnostics import SystemDiagnostic


class TestSystemDiagnostics(unittest.TestCase):
    @patch("modules.vision.VisionEngine.capture_screen")
    def test_run_diagnostics(self, mock_capture):
        """Tests SystemDiagnostic.run_diagnostics executes without error."""
        import numpy as np

        mock_capture.return_value = np.ones((100, 100), dtype=np.uint8) * 128
        results = SystemDiagnostic.run_diagnostics(verbose=False)

        self.assertIn("os_info", results)
        self.assertIn("dependencies", results)
        self.assertIn("screen_capture", results)
        self.assertIn("overall_status", results)
        self.assertIn(results["overall_status"], ["PASS", "WARN", "FAIL"])


if __name__ == "__main__":
    unittest.main()
