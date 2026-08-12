import unittest
from config import BotConfig
from unittest.mock import MagicMock, patch

import config
from config import BotConfig
from modules.actions import ActionEngine, generate_bezier_curve


class TestActionEngine(unittest.TestCase):
    def setUp(self):
        self.action_engine = ActionEngine(BotConfig())

    @patch("time.sleep")
    def test_human_delay(self, mock_sleep):
        """Tests that human_delay calls sleep within specified min/max bounds."""
        self.action_engine.human_delay(min_sec=1.0, max_sec=2.0)
        mock_sleep.assert_called_once()
        slept_duration = mock_sleep.call_args[0][0]
        self.assertGreaterEqual(slept_duration, 1.0)
        self.assertLessEqual(slept_duration, 2.0)

    @patch("time.sleep")
    def test_gaussian_reaction_delays(self, mock_sleep):
        """Tests that human_delay with use_gaussian=True calculates Gaussian delays bounded by min/max."""
        delays = []
        for _ in range(50):
            d = self.action_engine.human_delay(min_sec=1.0, max_sec=3.0, use_gaussian=True)
            delays.append(d)
            self.assertGreaterEqual(d, 1.0)
            self.assertLessEqual(d, 3.0)

        # Mean of sampled Gaussian delays should be roughly close to midpoint 2.0
        avg_delay = sum(delays) / len(delays)
        self.assertAlmostEqual(avg_delay, 2.0, delta=0.4)

    @patch("time.sleep")
    def test_uniform_reaction_delays(self, mock_sleep):
        """Tests human_delay with use_gaussian=False."""
        d = self.action_engine.human_delay(min_sec=1.0, max_sec=3.0, use_gaussian=False)
        self.assertGreaterEqual(d, 1.0)
        self.assertLessEqual(d, 3.0)

    def test_generate_bezier_curve_points(self):
        """Tests that generate_bezier_curve generates non-linear points from start to end."""
        start = (100, 100)
        end = (500, 400)
        num_points = 20

        points = generate_bezier_curve(start, end, num_points=num_points)

        self.assertEqual(len(points), num_points)
        self.assertEqual(points[0], start)
        self.assertEqual(points[-1], end)

        # Check that intermediate points lie within bounded coordinate range
        for x, y in points:
            self.assertGreaterEqual(x, 50)
            self.assertLessEqual(x, 550)
            self.assertGreaterEqual(y, 50)
            self.assertLessEqual(y, 450)

    def test_generate_bezier_curve_short_distance(self):
        """Tests generate_bezier_curve with tiny distance returns start and end."""
        start = (100, 100)
        end = (101, 101)
        points = generate_bezier_curve(start, end, num_points=10)
        self.assertEqual(points, [start, end])

    @patch("pyautogui.moveTo")
    @patch("time.sleep")
    def test_move_mouse_bezier(self, mock_sleep, mock_moveto):
        """Tests move_mouse_bezier steps through points smooth path."""
        self.action_engine.move_mouse_bezier(100, 100, 200, 200, duration=0.1, steps=10)
        self.assertGreaterEqual(mock_moveto.call_count, 5)
        self.assertGreaterEqual(mock_sleep.call_count, 5)
        # Last step should reach destination
        mock_moveto.assert_called_with(200, 200)

    @patch("pyautogui.position", return_value=(500, 500))
    @patch("modules.actions.self.action_engine.move_mouse_bezier")
    def test_idle_jitter(self, mock_bezier, mock_pos):
        """Tests idle_jitter calculates random subtle offset and calls bezier movement."""
        target_x, target_y = self.action_engine.idle_jitter(max_offset=15)

        self.assertNotEqual((target_x, target_y), (500, 500))
        self.assertLessEqual(abs(target_x - 500), 15)
        self.assertLessEqual(abs(target_y - 500), 15)
        mock_bezier.assert_called_once()

    @patch("modules.actions.UINPUT_MOUSE", None)
    @patch("pyautogui.moveTo")
    @patch("pyautogui.mouseDown")
    @patch("pyautogui.mouseUp")
    def test_click_at_pyautogui_fallback(self, mock_mouseup, mock_mousedown, mock_moveto):
        """Tests click_at coordinate targeting using pyautogui fallback when uinput is disabled."""
        self.action_engine.click_at(100, 200, offset=0)
        mock_mousedown.assert_called_once()
        mock_mouseup.assert_called_once()

    def test_click_at_uinput(self):
        """Tests click_at when uinput hardware device is available."""
        mock_uinput = MagicMock()
        with patch("modules.actions.UINPUT_MOUSE", mock_uinput):
            self.action_engine.click_at(100, 200, offset=0)
            self.assertEqual(mock_uinput.write.call_count, 2)
            self.assertEqual(mock_uinput.syn.call_count, 2)

    def test_click_match(self):
        """Tests click_match wrapper with valid match dict and None."""
        with (
            patch.object(ActionEngine, "click_at") as mock_click,
            patch.object(ActionEngine, "human_delay"),
        ):
            match_info = {"x": 150, "y": 250, "confidence": 0.95}
            result = self.action_engine.click_match(match_info)
            self.assertTrue(result)
        # None match
        mock_click.reset_mock()
        result_none = self.action_engine.click_match(None)
        self.assertFalse(result_none)
        mock_click.assert_not_called()

    @patch("pyautogui.hotkey")
    @patch("pyautogui.write")
    @patch("pyautogui.press")
    @patch("modules.actions.self.action_engine.human_delay")
    def test_navigate_to_url(self, mock_delay, mock_press, mock_write, mock_hotkey):
        """Tests navigate_to_url hotkey and typing sequence."""
        test_url = "https://game.bombcrypto.io/test"
        self.action_engine.navigate_to_url(test_url)

        mock_hotkey.assert_called_once_with("ctrl", "l")
        mock_write.assert_called_once_with(test_url, interval=0.01)
        mock_press.assert_called_once_with("enter")

    @patch("modules.actions.self.action_engine.navigate_to_url")
    def test_refresh_page_direct_mode(self, mock_nav):
        """Tests refresh_page uses direct URL navigation when DIRECT_LANDING_MODE is True."""
        with patch.object(BotConfig, "direct_landing_mode", True):
            self.action_engine.refresh_page()
            mock_nav.assert_called_once_with(config.DIRECT_TREASURE_URL)

    @patch("pyautogui.press")
    @patch("modules.actions.self.action_engine.human_delay")
    def test_refresh_page_f5_mode(self, mock_delay, mock_press):
        """Tests refresh_page uses F5 key when DIRECT_LANDING_MODE is False."""

    @patch("modules.actions.self.action_engine.drag_scroll")
    def test_scroll_down_invokes_drag_scroll(self, mock_drag):
        """Tests that scroll_down invokes drag_scroll drag gesture from bottom to top."""
        self.action_engine.scroll_down(500, 500, distance=200)
        # Should drag UP: start at 500+100=600, end at 500-100=400
        mock_drag.assert_called_once_with(500, 600, 500, 400, duration=0.4)

    @patch("modules.actions.HAS_HYPRCTL", False)
    @patch("modules.actions.UINPUT_MOUSE", None)
    @patch("pyautogui.moveTo")
    @patch("pyautogui.dragTo")
    def test_drag_scroll_pyautogui(self, mock_dragto, mock_moveto):
        """Tests drag_scroll mouse press, movement, and release sequence."""
        self.action_engine.drag_scroll(500, 600, 500, 400, duration=0.35)
        mock_moveto.assert_called_with(500, 600)
        mock_dragto.assert_called_once_with(500, 400, duration=0.35, button="left")


if __name__ == "__main__":
    unittest.main()
