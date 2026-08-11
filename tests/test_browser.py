import unittest
from unittest.mock import MagicMock, patch

import config
from modules.browser import BrowserManager


class TestBrowserManager(unittest.TestCase):
    @patch("subprocess.check_output")
    def test_get_attached_browser_info_running(self, mock_ps):
        """Tests detecting an active running Brave process from system process table."""
        mock_ps.return_value = (
            "  PID COMM             ARGS\n"
            " 1234 brave            /usr/bin/brave-browser --enable-automation\n"
        )
        info = BrowserManager.get_attached_browser_info()
        self.assertEqual(info["status"], "ATTACHED & RUNNING")
        self.assertEqual(info["pid"], "1234")
        self.assertIn("Brave", info["name"])

    @patch("subprocess.check_output")
    @patch("modules.browser.BrowserManager.find_browser_executable")
    def test_get_attached_browser_info_not_running(self, mock_find, mock_ps):
        """Tests output when browser process is not actively running."""
        mock_ps.return_value = "  PID COMM             ARGS\n 9999 bash             /bin/bash\n"
        mock_find.return_value = "/usr/bin/brave-browser"

        info = BrowserManager.get_attached_browser_info()
        self.assertEqual(info["status"], "NOT RUNNING (Auto-launch enabled)")
        self.assertEqual(info["exe"], "/usr/bin/brave-browser")

    @patch("os.path.exists")
    @patch("os.access")
    def test_find_brave_executable(self, mock_access, mock_exists):
        """Tests resolving known binary path for Brave."""
        mock_exists.side_effect = lambda path: path == "/opt/brave.com/brave/brave"
        mock_access.return_value = True

        exe = BrowserManager.find_brave_executable()
        self.assertEqual(exe, "/opt/brave.com/brave/brave")

    @patch("subprocess.Popen")
    @patch("modules.browser.BrowserManager.find_browser_executable")
    def test_launch_browser_custom_executable(self, mock_find, mock_popen):
        """Tests launching browser with specified executable path."""
        mock_find.return_value = "/usr/bin/google-chrome"
        result = BrowserManager.launch_browser("https://game.bombcrypto.io/test", "chrome")

        self.assertTrue(result)
        mock_popen.assert_called_once_with(
            ["/usr/bin/google-chrome", "https://game.bombcrypto.io/test"]
        )

    @patch("webbrowser.open")
    def test_launch_browser_default_fallback(self, mock_web_open):
        """Tests system default browser opening fallback."""
        mock_web_open.return_value = True
        result = BrowserManager.launch_browser("https://game.bombcrypto.io/test", "default")
        self.assertTrue(result)
        mock_web_open.assert_called_once_with("https://game.bombcrypto.io/test")

    @patch("os.path.exists", return_value=True)
    @patch("os.access", return_value=True)
    def test_custom_browser_executable_path_override(self, mock_access, mock_exists):
        """Tests custom BROWSER_EXECUTABLE_PATH configuration override."""
        custom_path = "/custom/path/to/mybrowser"
        with patch.object(config, "BROWSER_EXECUTABLE_PATH", custom_path):
            found = BrowserManager.find_browser_executable("brave")
            self.assertEqual(found, custom_path)

    @patch("subprocess.run")
    def test_windows_process_query(self, mock_run):
        """Tests Windows tasklist process table query when sys.platform is win32."""
        mock_res = MagicMock()
        mock_res.return_code = 0
        mock_res.returncode = 0
        mock_res.stdout = '"chrome.exe","4321","Console","1","50,000 K"'
        mock_run.return_value = mock_res

        with patch("sys.platform", "win32"):
            info = BrowserManager.get_attached_browser_info()
            self.assertEqual(info["status"], "ATTACHED & RUNNING")
            self.assertEqual(info["pid"], "4321")

    @patch("modules.browser.BrowserManager.get_attached_browser_info")
    @patch("modules.browser.BrowserManager.launch_browser")
    def test_verify_and_ensure_browser(self, mock_launch, mock_info):
        """Tests verify_and_ensure_browser triggers auto-launch if browser is not attached."""
        mock_info.return_value = {"status": "NOT RUNNING (Auto-launch enabled)"}
        BrowserManager.verify_and_ensure_browser()
        mock_launch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
