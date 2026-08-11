import time
import unittest
from unittest.mock import patch

import numpy as np

import config
from modules.bot_logic import BombCryptoBot, BotState, format_duration


class TestBombCryptoBotLogic(unittest.TestCase):
    def setUp(self):
        self.bot = BombCryptoBot()

    def test_format_duration(self):
        """Tests format_duration string formatting helper."""
        self.assertEqual(format_duration(0), "00:00:000")
        self.assertEqual(format_duration(-5), "00:00:000")
        self.assertEqual(format_duration(65.5), "01:05:500")
        self.assertEqual(format_duration(3665.123), "01:01:05:123")

    def test_env_config_hero_work_interval(self):
        """Tests environment variable loading for HERO_WORK_INTERVAL_MINUTES."""
        import importlib
        import os

        with patch.dict(os.environ, {"HERO_WORK_INTERVAL_MINUTES": "45.5"}):
            importlib.reload(config)
            self.assertEqual(config.HERO_WORK_INTERVAL_MINUTES, 45.5)

        # Restore default
        importlib.reload(config)

    def test_initial_state(self):
        """Tests default initialization state and parameters."""
        self.assertEqual(self.bot.state, BotState.INITIALIZING)
        self.assertEqual(self.bot.last_hero_work_time, 0)
        self.assertAlmostEqual(self.bot.last_progress_time, time.time(), delta=2.0)

    def test_state_transitions(self):
        """Tests set_state state change tracking."""
        self.bot.set_state(BotState.LOGGING_IN)
        self.assertEqual(self.bot.state, BotState.LOGGING_IN)

        self.bot.set_state(BotState.SENDING_HEROES)
        self.assertEqual(self.bot.state, BotState.SENDING_HEROES)

    def test_check_stuck_timeout_triggered(self):
        """Tests that exceeding MAX_STUCK_TIMEOUT_MINUTES sets state to STUCK_RECOVERY."""
        # Set progress timestamp 15 minutes in the past
        self.bot.last_progress_time = time.time() - (config.MAX_STUCK_TIMEOUT_MINUTES + 5) * 60

        is_stuck = self.bot.check_stuck_timeout()
        self.assertTrue(is_stuck)
        self.assertEqual(self.bot.state, BotState.STUCK_RECOVERY)

    def test_check_stuck_timeout_not_triggered(self):
        """Tests that recent activity prevents stuck timeout."""
        self.bot.last_progress_time = time.time() - 60  # 1 minute ago
        is_stuck = self.bot.check_stuck_timeout()
        self.assertFalse(is_stuck)
        self.assertEqual(self.bot.state, BotState.INITIALIZING)

    @patch("modules.actions.ActionEngine.refresh_page")
    def test_handle_stuck_recovery(self, mock_refresh):
        """Tests recovery execution (refreshing page & state reset)."""
        self.bot.set_state(BotState.STUCK_RECOVERY)
        self.bot.handle_stuck_recovery()

        mock_refresh.assert_called_once()
        self.assertEqual(self.bot.state, BotState.INITIALIZING)
        self.assertAlmostEqual(self.bot.last_progress_time, time.time(), delta=2.0)

    @patch("modules.vision.VisionEngine.find_template")
    @patch("modules.vision.VisionEngine.capture_screen")
    @patch("modules.actions.ActionEngine.click_match")
    def test_check_errors_or_disconnect(self, mock_click, mock_capture, mock_find):
        """Tests handling error modals when detected on screen."""
        mock_capture.return_value = np.zeros((100, 100), dtype=np.uint8)

        # Simulate finding error_ok button
        mock_find.side_effect = lambda key, **k: (
            {"x": 50, "y": 50, "confidence": 0.9} if "error_ok" in key else None
        )

        handled = self.bot.check_errors_or_disconnect()
        self.assertTrue(handled)
        mock_click.assert_called_once()

    @patch("modules.vision.VisionEngine.find_template")
    @patch("modules.vision.VisionEngine.capture_screen")
    @patch("modules.actions.ActionEngine.click_match")
    @patch("modules.actions.ActionEngine.human_delay")
    def test_handle_login_confirm_profile(self, mock_delay, mock_click, mock_capture, mock_find):
        """Tests confirm profile OK popup flow."""
        mock_capture.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_find.side_effect = lambda key, **k: (
            {"x": 50, "y": 50, "confidence": 0.85} if "confirm_profile" in key else None
        )

        handled = self.bot.handle_login()
        self.assertTrue(handled)
        mock_click.assert_called_once()

    @patch.object(config, "DIRECT_LANDING_MODE", True)
    def test_enter_treasure_hunt_direct_mode(self):
        """Tests direct landing mode skips menu icon matching."""
        result = self.bot.enter_treasure_hunt()
        self.assertTrue(result)

    @patch("modules.vision.VisionEngine.find_template")
    @patch("modules.vision.VisionEngine.capture_screen")
    @patch("modules.actions.ActionEngine.click_match")
    @patch("modules.actions.ActionEngine.click_at")
    @patch("modules.actions.ActionEngine.human_delay")
    def test_send_heroes_to_work_flow(
        self, mock_delay, mock_click_at, mock_click_match, mock_capture, mock_find
    ):
        """Tests complete hero menu expansion, work all click, close modal, and collapse sequence."""
        dummy_screen = np.zeros((100, 100), dtype=np.uint8)
        mock_capture.return_value = dummy_screen

        def find_side_effect(target_path, **kwargs):
            if "arrow_menu_button" in target_path:
                return {"x": 10, "y": 90, "confidence": 0.8}
            elif "heroes_icon" in target_path:
                return {"x": 20, "y": 90, "confidence": 0.85}
            elif "work_all_button" in target_path:
                return {"x": 50, "y": 50, "confidence": 0.9}
            elif "close_button" in target_path:
                return {"x": 80, "y": 20, "confidence": 0.88}
            return None

        mock_find.side_effect = find_side_effect

        success = self.bot.send_heroes_to_work()
        self.assertTrue(success)
        self.assertGreater(self.bot.last_hero_work_time, 0)
        self.assertEqual(mock_click_match.call_count, 4)
        mock_click_at.assert_called_once_with(50, 50)  # Screen center click to collapse HUD

    @patch("modules.vision.VisionEngine.find_template")
    @patch("modules.vision.VisionEngine.capture_screen")
    @patch("modules.actions.ActionEngine.click_match")
    @patch("modules.actions.ActionEngine.click_at")
    @patch("modules.actions.ActionEngine.human_delay")
    def test_send_heroes_to_work_all_already_working(
        self, mock_delay, mock_click_at, mock_click_match, mock_capture, mock_find
    ):
        """Tests that when rest_all_button is detected, the bot does not click rest_all_button."""
        dummy_screen = np.zeros((100, 100), dtype=np.uint8)
        mock_capture.return_value = dummy_screen

        def find_side_effect(target_path, **kwargs):
            if "arrow_menu_button" in target_path:
                return {"x": 10, "y": 90, "confidence": 0.8}
            elif "heroes_icon" in target_path:
                return {"x": 20, "y": 90, "confidence": 0.85}
            elif "rest_all_button" in target_path:
                return {"x": 50, "y": 50, "confidence": 0.9}
            elif "work_all_button" in target_path:
                return {"x": 50, "y": 50, "confidence": 0.9}
            elif "close_button" in target_path:
                return {"x": 80, "y": 20, "confidence": 0.88}
            return None

        mock_find.side_effect = find_side_effect

        success = self.bot.send_heroes_to_work()
        self.assertTrue(success)
        self.assertGreater(self.bot.last_hero_work_time, 0)
        # Should click arrow_menu_button, heroes_icon, close_button (3 match clicks) and NOT rest_all_button
        self.assertEqual(mock_click_match.call_count, 3)
        for call_arg in mock_click_match.call_args_list:
            matched_obj = call_arg[0][0]
            # Verify no click was made on rest_all location
            self.assertNotEqual(matched_obj, {"x": 50, "y": 50, "confidence": 0.9})
        mock_click_at.assert_called_once_with(50, 50)

    @patch("modules.vision.VisionEngine.find_template")
    @patch("modules.vision.VisionEngine.capture_screen")
    @patch("modules.actions.ActionEngine.click_match")
    @patch("modules.actions.ActionEngine.human_delay")
    def test_check_map_cleared_button_detected(
        self, mock_delay, mock_click, mock_capture, mock_find
    ):
        """Tests map clear button detection, state transition, and progress update."""
        mock_capture.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_find.side_effect = lambda key, **k: (
            {"x": 50, "y": 50, "confidence": 0.85} if "map_complete_button" in key else None
        )

        handled = self.bot.check_map_cleared()
        self.assertTrue(handled)
        mock_click.assert_called_once()
        self.assertEqual(self.bot.state, BotState.RESTING)

    @patch("modules.vision.VisionEngine.find_template")
    @patch("modules.vision.VisionEngine.capture_screen")
    @patch("modules.actions.ActionEngine.click_match")
    @patch("modules.actions.ActionEngine.human_delay")
    def test_check_map_cleared_modal_fallback(
        self, mock_delay, mock_click, mock_capture, mock_find
    ):
        """Tests map clear modal fallback detection when button target is missing."""
        mock_capture.return_value = np.zeros((100, 100), dtype=np.uint8)
        mock_find.side_effect = lambda key, **k: (
            {"x": 50, "y": 50, "confidence": 0.80} if "map_complete.png" in key else None
        )

        handled = self.bot.check_map_cleared()
        self.assertTrue(handled)
        mock_click.assert_called_once()
        self.assertEqual(self.bot.state, BotState.RESTING)

    @patch("modules.vision.VisionEngine.find_template", return_value=None)
    @patch("modules.vision.VisionEngine.capture_screen")
    def test_check_map_cleared_none(self, mock_capture, mock_find):
        """Tests check_map_cleared when no map complete banner/button is visible."""
        mock_capture.return_value = np.zeros((100, 100), dtype=np.uint8)
        handled = self.bot.check_map_cleared()
        self.assertFalse(handled)

    @patch("modules.actions.ActionEngine.idle_jitter")
    def test_check_idle_jitter_triggered(self, mock_jitter):
        """Tests BombCryptoBot triggers idle jitter when RESTING and interval elapsed."""
        self.bot.set_state(BotState.RESTING)
        self.bot.last_idle_jitter_time = time.time() - (config.IDLE_JITTER_INTERVAL_SECONDS + 5)

        self.bot.check_idle_jitter()

        mock_jitter.assert_called_once()
        self.assertAlmostEqual(self.bot.last_idle_jitter_time, time.time(), delta=2.0)

    @patch("modules.actions.ActionEngine.idle_jitter")
    def test_check_idle_jitter_not_resting(self, mock_jitter):
        """Tests BombCryptoBot does not trigger idle jitter if not in RESTING state."""
        self.bot.set_state(BotState.SENDING_HEROES)
        self.bot.last_idle_jitter_time = time.time() - 100

        self.bot.check_idle_jitter()

        mock_jitter.assert_not_called()

    @patch.object(config, "ONLY_REFRESH_ON_ERROR", False)
    @patch.object(config, "REFRESH_INTERVAL_MINUTES", 15.0)
    @patch("modules.actions.ActionEngine.refresh_page")
    def test_check_periodic_refresh_triggered(self, mock_refresh):
        """Tests periodic refresh triggers page refresh when interval has elapsed."""
        self.bot.last_periodic_refresh_time = time.time() - (15 * 60 + 10)
        refreshed = self.bot.check_periodic_refresh()
        self.assertTrue(refreshed)
        mock_refresh.assert_called_once()
        self.assertEqual(self.bot.state, BotState.INITIALIZING)

    @patch.object(config, "ONLY_REFRESH_ON_ERROR", True)
    @patch.object(config, "REFRESH_INTERVAL_MINUTES", 15.0)
    @patch("modules.actions.ActionEngine.refresh_page")
    def test_check_periodic_refresh_combined_mode(self, mock_refresh):
        """Tests periodic refresh triggers even if ONLY_REFRESH_ON_ERROR is also True when interval > 0."""
        self.bot.last_periodic_refresh_time = time.time() - (15 * 60 + 10)
        refreshed = self.bot.check_periodic_refresh()
        self.assertTrue(refreshed)
        mock_refresh.assert_called_once()
        self.assertEqual(self.bot.state, BotState.INITIALIZING)

    @patch.object(config, "ONLY_REFRESH_ON_ERROR", True)
    @patch.object(config, "ENABLE_HERO_WORK_ACTIONS", False)
    @patch.object(config, "DIRECT_LANDING_MODE", True)
    @patch("modules.vision.VisionEngine.capture_screen")
    @patch("modules.vision.VisionEngine.find_template", return_value=None)
    @patch("modules.bot_logic.BombCryptoBot.send_heroes_to_work")
    def test_run_cycle_only_refresh_on_error(self, mock_send_heroes, mock_find, mock_capture):
        """Tests that run_cycle in ONLY_REFRESH_ON_ERROR mode skips hero work clicks."""
        mock_capture.return_value = np.zeros((100, 100), dtype=np.uint8)
        self.bot.run_cycle()
        mock_send_heroes.assert_not_called()
        self.assertEqual(self.bot.state, BotState.RESTING)


if __name__ == "__main__":
    unittest.main()
