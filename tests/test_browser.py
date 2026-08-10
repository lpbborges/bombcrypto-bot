import unittest
from unittest.mock import patch

from modules.browser import BraveManager


class TestBraveManager(unittest.TestCase):
    @patch("subprocess.check_output")
    def test_get_attached_browser_info_running(self, mock_ps):
        """Tests detecting an active running Brave process from system process table."""
        mock_ps.return_value = (
            "  PID COMM             ARGS\n"
            " 1234 brave            /usr/bin/brave-browser --enable-automation\n"
        )
        info = BraveManager.get_attached_browser_info()
        self.assertEqual(info["status"], "ATTACHED & RUNNING")
        self.assertEqual(info["pid"], "1234")
        self.assertIn("Brave", info["name"])

    @patch("subprocess.check_output")
    @patch("modules.browser.BraveManager.find_brave_executable")
    def test_get_attached_browser_info_not_running(self, mock_find, mock_ps):
        """Tests output when browser process is not actively running."""
        mock_ps.return_value = "  PID COMM             ARGS\n 9999 bash             /bin/bash\n"
        mock_find.return_value = "/usr/bin/brave-browser"

        info = BraveManager.get_attached_browser_info()
        self.assertEqual(info["status"], "NOT RUNNING (Auto-launch enabled)")
        self.assertEqual(info["exe"], "/usr/bin/brave-browser")

    @patch("os.path.exists")
    @patch("os.access")
    def test_find_brave_executable(self, mock_access, mock_exists):
        """Tests resolving known binary path for Brave."""
        mock_exists.side_effect = lambda path: path == "/opt/brave.com/brave/brave"
        mock_access.return_value = True

        exe = BraveManager.find_brave_executable()
        self.assertEqual(exe, "/opt/brave.com/brave/brave")

    @patch("subprocess.Popen")
    @patch("modules.browser.BraveManager.find_brave_executable")
    def test_launch_brave(self, mock_find, mock_popen):
        """Tests launching Brave binary with direct target URL."""
        mock_find.return_value = "/usr/bin/brave-browser"
        result = BraveManager.launch_brave("https://game.bombcrypto.io/test")

        self.assertTrue(result)
        mock_popen.assert_called_once_with(
            ["/usr/bin/brave-browser", "https://game.bombcrypto.io/test"]
        )

    @patch("modules.browser.BraveManager.get_attached_browser_info")
    @patch("modules.browser.BraveManager.launch_brave")
    def test_verify_and_ensure_brave(self, mock_launch, mock_info):
        """Tests verify_and_ensure_brave triggers auto-launch if browser is not attached."""
        mock_info.return_value = {"status": "NOT RUNNING (Auto-launch enabled)"}
        BraveManager.verify_and_ensure_brave()
        mock_launch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
