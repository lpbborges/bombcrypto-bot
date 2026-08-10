import unittest
from unittest.mock import MagicMock, patch

import config
from modules.actions import ActionEngine


class TestActionEngine(unittest.TestCase):
    @patch("time.sleep")
    def test_human_delay(self, mock_sleep):
        """Tests that human_delay calls sleep within specified min/max bounds."""
        ActionEngine.human_delay(min_sec=1.0, max_sec=2.0)
        mock_sleep.assert_called_once()
        slept_duration = mock_sleep.call_args[0][0]
        self.assertGreaterEqual(slept_duration, 1.0)
        self.assertLessEqual(slept_duration, 2.0)

    @patch("modules.actions.UINPUT_MOUSE", None)
    @patch("pyautogui.moveTo")
    @patch("pyautogui.mouseDown")
    @patch("pyautogui.mouseUp")
    def test_click_at_pyautogui_fallback(self, mock_mouseup, mock_mousedown, mock_moveto):
        """Tests click_at coordinate targeting using pyautogui fallback when uinput is disabled."""
        ActionEngine.click_at(100, 200, offset=0)
        mock_moveto.assert_called_with(100, 200)
        mock_mousedown.assert_called_once()
        mock_mouseup.assert_called_once()

    def test_click_at_uinput(self):
        """Tests click_at when uinput hardware device is available."""
        mock_uinput = MagicMock()
        with patch("modules.actions.UINPUT_MOUSE", mock_uinput):
            ActionEngine.click_at(100, 200, offset=0)
            self.assertEqual(mock_uinput.write.call_count, 2)
            self.assertEqual(mock_uinput.syn.call_count, 2)

    def test_click_match(self):
        """Tests click_match wrapper with valid match dict and None."""
        with (
            patch.object(ActionEngine, "click_at") as mock_click,
            patch.object(ActionEngine, "human_delay"),
        ):
            match_info = {"x": 150, "y": 250, "confidence": 0.95}
            result = ActionEngine.click_match(match_info)
            self.assertTrue(result)
        # None match
        mock_click.reset_mock()
        result_none = ActionEngine.click_match(None)
        self.assertFalse(result_none)
        mock_click.assert_not_called()

    @patch("pyautogui.hotkey")
    @patch("pyautogui.write")
    @patch("pyautogui.press")
    @patch("modules.actions.ActionEngine.human_delay")
    def test_navigate_to_url(self, mock_delay, mock_press, mock_write, mock_hotkey):
        """Tests navigate_to_url hotkey and typing sequence."""
        test_url = "https://game.bombcrypto.io/test"
        ActionEngine.navigate_to_url(test_url)

        mock_hotkey.assert_called_once_with("ctrl", "l")
        mock_write.assert_called_once_with(test_url, interval=0.01)
        mock_press.assert_called_once_with("enter")

    @patch("modules.actions.ActionEngine.navigate_to_url")
    def test_refresh_page_direct_mode(self, mock_nav):
        """Tests refresh_page uses direct URL navigation when DIRECT_LANDING_MODE is True."""
        with patch.object(config, "DIRECT_LANDING_MODE", True):
            ActionEngine.refresh_page()
            mock_nav.assert_called_once_with(config.DIRECT_TREASURE_URL)

    @patch("pyautogui.press")
    @patch("modules.actions.ActionEngine.human_delay")
    def test_refresh_page_f5_mode(self, mock_delay, mock_press):
        """Tests refresh_page uses F5 key when DIRECT_LANDING_MODE is False."""
        with patch.object(config, "DIRECT_LANDING_MODE", False):
            ActionEngine.refresh_page()
            mock_press.assert_called_once_with("f5")


if __name__ == "__main__":
    unittest.main()
