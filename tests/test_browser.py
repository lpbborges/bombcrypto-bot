import unittest
from unittest.mock import MagicMock, patch

from config import BotConfig
from modules.browser import BrowserManager


class TestBrowserManager(unittest.TestCase):
    def setUp(self):
        self.browser_manager = BrowserManager()
        self.browser_manager.config = BotConfig()
        BrowserManager.config = BotConfig()

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
        BrowserManager.config.browser_executable_path = custom_path
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

    @patch("sys.platform", "darwin")
    @patch(
        "shutil.which", return_value="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    )
    def test_find_brave_executable_darwin(self, mock_which):
        """Tests locating Brave binary using shutil.which."""
        path = BrowserManager.find_browser_executable("brave")
        self.assertEqual(path, "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")

    @patch("modules.browser.BrowserManager.get_attached_browser_info")
    @patch("modules.browser.BrowserManager.launch_browser")
    def test_verify_and_ensure_browser(self, mock_launch, mock_info):
        """Tests verify_and_ensure_browser triggers auto-launch if browser is not attached."""
        mock_info.return_value = {"status": "NOT RUNNING (Auto-launch enabled)"}
        BrowserManager.verify_and_ensure_browser()
        mock_launch.assert_called_once()

    @patch("modules.browser.BrowserManager.get_url_from_process_args")
    def test_detect_game_version_v10l_url(self, mock_process_url):
        """Tests auto-detecting v10l from browser process URL."""
        mock_process_url.return_value = "https://game.bombcrypto.io/web/v10l/index.html"
        version = BrowserManager.detect_game_version()
        self.assertEqual(version, "v10l")

    @patch("modules.browser.BrowserManager.get_url_from_process_args")
    def test_detect_game_version_v13d_url(self, mock_process_url):
        """Tests auto-detecting v13d from browser process URL."""
        mock_process_url.return_value = (
            "https://game.bombcrypto.io/web/v13d/index.html?landing=treasure"
        )
        version = BrowserManager.detect_game_version()
        self.assertEqual(version, "v13d")

    @patch("modules.browser.BrowserManager.get_url_from_process_args", return_value=None)
    @patch("modules.browser.BrowserManager.get_browser_window_title")
    def test_detect_game_version_v10l_window_title(self, mock_title, mock_process_url):
        """Tests auto-detecting v10l from active browser window title."""
        mock_title.return_value = "Bomb Crypto Game - v10l"
        version = BrowserManager.detect_game_version()
        self.assertEqual(version, "v10l")

    @patch("modules.browser.BrowserManager.detect_game_version")
    @patch("modules.browser.BrowserManager.get_open_browser_url")
    def test_sync_game_version_from_browser(self, mock_url, mock_version):
        """Tests syncing config GAME_VERSION and DIRECT_LANDING_MODE based on detected URL."""
        mock_url.return_value = "https://game.bombcrypto.io/web/v10l/index.html"
        mock_version.return_value = "v10l"

        synced_ver = BrowserManager.sync_game_version_from_browser()
        self.assertEqual(synced_ver, "v10l")
        self.assertEqual(BrowserManager.config.game_version, "v10l")
        self.assertFalse(BrowserManager.config.direct_landing_mode)
        self.assertEqual(
            BrowserManager.config.direct_treasure_url,
            "https://game.bombcrypto.io/web/v10l/index.html",
        )

    @patch("modules.platform_utils.is_linux", return_value=True)
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_focus_game_window_linux_wmctrl(self, mock_run, mock_which, mock_is_linux):
        """Tests focusing game window on Linux using wmctrl."""
        mock_which.side_effect = lambda cmd: cmd == "wmctrl"

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "0x02000003  0 brave-browser.Brave-browser user-pc bombcrypto\n"
        mock_run.return_value = mock_res

        result = BrowserManager.focus_game_window()
        self.assertTrue(result)
        mock_run.assert_called_with(["wmctrl", "-i", "-a", "0x02000003"], timeout=2)

    @patch("modules.platform_utils.is_linux", return_value=False)
    @patch("modules.platform_utils.is_windows", return_value=True)
    @patch("subprocess.run")
    def test_focus_game_window_windows(self, mock_run, mock_is_windows, mock_is_linux):
        """Tests focusing game window on Windows."""
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res

        result = BrowserManager.focus_game_window()
        self.assertTrue(result)
        mock_run.assert_called_once()
        self.assertIn("Get-Process", mock_run.call_args[0][0][3])


if __name__ == "__main__":
    unittest.main()
