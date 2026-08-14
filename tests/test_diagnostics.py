from __future__ import annotations

import unittest
from unittest.mock import patch

from config import BotConfig
from modules.diagnostics import SystemDiagnostic


class TestSystemDiagnostics(unittest.TestCase):
    @patch("modules.vision.VisionEngine.capture_screen")
    def test_run_diagnostics_default_config(self, mock_capture):
        """Tests SystemDiagnostic.run_diagnostics executes with default config=None without TypeError."""
        import numpy as np

        mock_capture.return_value = np.ones((100, 100), dtype=np.uint8) * 128
        results = SystemDiagnostic.run_diagnostics()

        self.assertIn("os_info", results)
        self.assertIn("dependencies", results)
        self.assertIn("browser", results)
        self.assertIn("overall_status", results)

    @patch("modules.vision.VisionEngine.capture_screen")
    def test_run_diagnostics_explicit_config(self, mock_capture):
        """Tests SystemDiagnostic.run_diagnostics executes with explicit BotConfig instance."""
        import numpy as np

        mock_capture.return_value = np.ones((100, 100), dtype=np.uint8) * 128
        cfg = BotConfig()
        results = SystemDiagnostic.run_diagnostics(config=cfg, verbose=False)

        self.assertIn("os_info", results)
        self.assertIn("overall_status", results)
        self.assertIn(results["overall_status"], ["PASS", "WARN", "FAIL"])

    @patch("builtins.input")
    @patch("builtins.open")
    def test_run_setup_wizard(self, mock_open, mock_input):
        """Tests run_setup_wizard executes and writes configuration without AttributeError."""
        from modules.diagnostics import run_setup_wizard

        mock_input.side_effect = [
            "v13d",  # game version
            "30",  # interval
            "brave",  # browser
            "n",  # only refresh on error
            "",  # discord url
            "",  # telegram token
            "",  # telegram chat
        ]

        run_setup_wizard()
        mock_open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
