import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from config import BotConfig
from modules.vision import VisionEngine


class TestVisionEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.vision = VisionEngine(BotConfig())

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_frame_caching_and_invalidation(self):
        """Tests screen frame caching and clear_cache behavior."""
        dummy_frame = np.ones((50, 50), dtype=np.uint8) * 128
        self.vision._cached_screen = dummy_frame

        # Cache retrieval
        cached = self.vision.capture_screen(force_refresh=False)
        self.assertIs(cached, dummy_frame)

        # Invalidation
        self.vision.clear_cache()
        self.assertIsNone(self.vision._cached_screen)

    def test_template_caching_and_invalidation(self):
        """Tests template image caching and clear_template_cache behavior."""
        template_path = os.path.join(self.temp_dir, "cached_template.png")
        dummy_img = np.ones((20, 20), dtype=np.uint8) * 200
        cv2.imwrite(template_path, dummy_img)

        # First load should read from disk and store in cache
        loaded = self.vision._load_template(template_path)
        self.assertIsNotNone(loaded)
        self.assertIn(template_path, self.vision._template_cache)

        # Invalidation
        self.vision.clear_template_cache()
        self.assertEqual(len(self.vision._template_cache), 0)

    def test_find_template_exact_match(self):
        """Tests multi-scale template matching with a synthetic generated image."""
        # Create 200x200 canvas
        canvas = np.zeros((200, 200), dtype=np.uint8)

        # Create textured template (40x40 circle pattern with variance)
        template = np.zeros((40, 40), dtype=np.uint8)
        cv2.circle(template, (20, 20), 15, 255, -1)
        cv2.circle(template, (20, 20), 8, 100, -1)
        template_path = os.path.join(self.temp_dir, "pattern.png")
        cv2.imwrite(template_path, template)

        # Place the exact template at center (top_left x=80, y=80 -> center x=100, y=100)
        canvas[80:120, 80:120] = template

        match = self.vision.find_template(template_path, threshold=0.9, screen_gray=canvas)
        self.assertIsNotNone(match)
        self.assertAlmostEqual(match["x"], 100, delta=2)
        self.assertAlmostEqual(match["y"], 100, delta=2)
        self.assertGreaterEqual(match["confidence"], 0.9)

    def test_find_template_non_existent_file(self):
        """Tests that passing a non-existent file returns None without raising an exception."""
        result = self.vision.find_template(
            "/non/existent/path.png", screen_gray=np.zeros((10, 10), dtype=np.uint8)
        )
        self.assertIsNone(result)

    def test_find_all_templates(self):
        """Tests finding multiple occurrences of a target template."""
        canvas = np.zeros((300, 300), dtype=np.uint8)

        # Create textured template (30x30 pattern)
        template = np.zeros((30, 30), dtype=np.uint8)
        cv2.rectangle(template, (5, 5), (25, 25), 255, -1)
        cv2.circle(template, (15, 15), 5, 50, -1)
        template_path = os.path.join(self.temp_dir, "multi_pattern.png")
        cv2.imwrite(template_path, template)

        # Place template at two distinct positions far apart
        canvas[30:60, 30:60] = template
        canvas[200:230, 200:230] = template

        matches = self.vision.find_all_templates(template_path, threshold=0.9, screen_gray=canvas)
        self.assertEqual(len(matches), 2)

    def test_wayland_detection(self):
        """Tests Wayland environment detection check."""
        with (
            patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}),
            patch("shutil.which", return_value="/usr/bin/grim"),
        ):
            self.assertTrue(self.vision._check_wayland_grim())

    def test_find_template_roi_inside(self):
        """Tests that ROI bounding finds template and calculates correct full-screen coordinates."""
        canvas = np.zeros((200, 200), dtype=np.uint8)
        template = np.zeros((30, 30), dtype=np.uint8)
        cv2.rectangle(template, (5, 5), (25, 25), 255, -1)
        template_path = os.path.join(self.temp_dir, "roi_target.png")
        cv2.imwrite(template_path, template)

        # Place template in bottom half (y=150 to 180, x=50 to 80 -> center x=65, y=165)
        canvas[150:180, 50:80] = template

        # ROI for bottom half (ymin=0.5, xmin=0.0, ymax=1.0, xmax=1.0)
        match = self.vision.find_template(
            template_path, threshold=0.9, screen_gray=canvas, roi=(0.5, 0.0, 1.0, 1.0)
        )
        self.assertIsNotNone(match)
        self.assertAlmostEqual(match["x"], 65, delta=2)
        self.assertAlmostEqual(match["y"], 165, delta=2)

    def test_find_template_roi_outside(self):
        """Tests that template outside designated ROI is not matched."""
        canvas = np.zeros((200, 200), dtype=np.uint8)
        template = np.zeros((30, 30), dtype=np.uint8)
        cv2.rectangle(template, (5, 5), (25, 25), 255, -1)
        template_path = os.path.join(self.temp_dir, "roi_outside_target.png")
        cv2.imwrite(template_path, template)

        # Place template in top half (y=20 to 50, x=50 to 80)
        canvas[20:50, 50:80] = template

        # ROI restricted to bottom half (ymin=0.6, xmin=0.0, ymax=1.0, xmax=1.0)
        match = self.vision.find_template(
            template_path, threshold=0.9, screen_gray=canvas, roi=(0.6, 0.0, 1.0, 1.0)
        )
        self.assertIsNone(match)

    def test_target_threshold_and_roi_config_resolution(self):
        """Tests automatic lookup of target-specific thresholds and ROIs from config."""
        from config import BotConfig

        self.assertEqual(BotConfig().get_target_threshold("bottom_arrow"), 0.70)
        self.assertEqual(BotConfig().get_target_threshold("confirm_profile_ok"), 0.75)
        self.assertEqual(BotConfig().get_target_roi("bottom_arrow"), (0.60, 0.0, 1.0, 1.0))
        self.assertIsNone(BotConfig().get_target_roi("non_existent_target"))

    def test_capture_screen_mss_xprotoerror_fallback(self):
        """Tests that X11 Protocol Error during mss grab is caught and falls back safely without crashing."""
        self.vision.use_wayland_grim = False
        mock_sct = MagicMock()
        mock_sct.monitors = [{"top": 0, "left": 0, "width": 1920, "height": 1080}]
        mock_sct.grab.side_effect = Exception("X11 Protocol Error: X Error of failed request: 8")
        self.vision.sct = mock_sct

        with (
            patch("shutil.which", return_value=None),
            patch.object(
                self.vision,
                "_capture_via_pil_imagegrab",
                return_value=np.ones((100, 100), dtype=np.uint8) * 50,
            ),
        ):
            screen = self.vision.capture_screen(force_refresh=True)
            self.assertIsNotNone(screen)
            self.assertEqual(screen.shape, (100, 100))
            self.assertEqual(screen[0, 0], 50)

    def test_capture_screen_monitor_index_out_of_bounds(self):
        """Tests that invalid monitor_index falls back gracefully to available monitors."""
        self.vision.monitor_index = 99  # Invalid monitor index
        mock_sct = MagicMock()
        mock_sct.monitors = [
            {"top": 0, "left": 0, "width": 1920, "height": 1080}
        ]  # Only 1 monitor (index 0)
        dummy_bgra = np.ones((100, 100, 4), dtype=np.uint8) * 200
        mock_sct.grab.return_value = dummy_bgra
        self.vision.sct = mock_sct

        img = self.vision._capture_via_mss()
        self.assertIsNotNone(img)
        mock_sct.grab.assert_called_once_with(mock_sct.monitors[0])

    def test_conditional_grim_error_logging(self):
        """Tests that Wayland-specific error advice is logged on Linux/Wayland capture failures."""
        self.vision.use_wayland_grim = False

        # 1. On Wayland without working capture -> Wayland Xorg instruction logged
        with (
            patch("modules.vision.sys.platform", "linux"),
            patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}),
            patch("modules.vision.shutil.which", return_value=None),
            patch.object(self.vision, "_capture_via_mss", return_value=None),
            patch.object(self.vision, "_capture_via_pil_imagegrab", return_value=None),
            patch.object(self.vision, "_capture_via_cli_utils", return_value=None),
            self.assertLogs("BombCryptoBot", level="ERROR") as cm,
        ):
            self.vision.capture_screen(force_refresh=True)
            self.assertTrue(any("Ubuntu on Xorg" in log for log in cm.output))

        # 2. On X11 / non-Wayland -> standard error logged without Wayland instruction
        self.vision.clear_cache()
        with (
            patch("modules.vision.sys.platform", "linux"),
            patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=True),
            patch("modules.vision.shutil.which", return_value=None),
            patch.object(self.vision, "_capture_via_mss", return_value=None),
            patch.object(self.vision, "_capture_via_pil_imagegrab", return_value=None),
            patch.object(self.vision, "_capture_via_cli_utils", return_value=None),
            self.assertLogs("BombCryptoBot", level="ERROR") as cm,
        ):
            self.vision.capture_screen(force_refresh=True)
            self.assertFalse(any("Ubuntu on Xorg" in log for log in cm.output))

    def test_identify_screen_various_states(self):
        """Tests screen identification for various game screens."""
        from modules.vision import GameScreen

        dummy_screen = np.zeros((100, 100), dtype=np.uint8)

        # Test Error Modal
        with patch.object(self.vision, "find_template") as mock_find:
            mock_find.side_effect = lambda key, **k: (
                {"x": 10, "y": 10} if "error_ok" in key else None
            )
            screen_type, matches = self.vision.identify_screen(screen_gray=dummy_screen)
            self.assertEqual(screen_type, GameScreen.ERROR_MODAL)

        # Test Login Screen
        with patch.object(self.vision, "find_template") as mock_find:
            mock_find.side_effect = lambda key, **k: (
                {"x": 10, "y": 10} if "connect_wallet" in key else None
            )
            screen_type, matches = self.vision.identify_screen(screen_gray=dummy_screen)
            self.assertEqual(screen_type, GameScreen.LOGIN)

        # Test Heroes Modal
        with patch.object(self.vision, "find_template") as mock_find:
            mock_find.side_effect = lambda key, **k: (
                {"x": 10, "y": 10} if "work_all_button" in key else None
            )
            screen_type, matches = self.vision.identify_screen(screen_gray=dummy_screen)
            self.assertEqual(screen_type, GameScreen.HEROES_MODAL)

        # Test Main Menu
        with patch.object(self.vision, "find_template") as mock_find:
            mock_find.side_effect = lambda key, **k: (
                {"x": 10, "y": 10} if "treasure_hunt" in key else None
            )
            screen_type, matches = self.vision.identify_screen(screen_gray=dummy_screen)
            self.assertEqual(screen_type, GameScreen.MAIN_MENU)

        # Test Map Cleared
        with patch.object(self.vision, "find_template") as mock_find:
            mock_find.side_effect = lambda key, **k: (
                {"x": 10, "y": 10} if "map_complete_button" in key else None
            )
            screen_type, matches = self.vision.identify_screen(screen_gray=dummy_screen)
            self.assertEqual(screen_type, GameScreen.MAP_CLEARED)

        # Test Unknown Screen
        with patch.object(self.vision, "find_template", return_value=None):
            screen_type, matches = self.vision.identify_screen(screen_gray=dummy_screen)
            self.assertEqual(screen_type, GameScreen.UNKNOWN)

    def test_pre_scaled_template_caching(self):
        """Tests that pre-scaled template images are cached for performance optimization."""
        template_path = os.path.join(self.temp_dir, "scaled_pattern.png")
        dummy_img = np.ones((30, 30), dtype=np.uint8) * 150
        cv2.imwrite(template_path, dummy_img)

        scales = [1.0, 0.90, 1.10]
        scaled_dict = self.vision._get_scaled_templates(template_path, scales)
        self.assertIn(1.0, scaled_dict)
        self.assertIn(0.90, scaled_dict)
        self.assertIn(1.10, scaled_dict)
        self.assertIn(template_path, self.vision._template_cache)

    def test_monitor_offset_translation(self):
        """Tests that monitor left/top offsets are correctly added to match coordinates for multi-monitor setups."""
        canvas = np.zeros((200, 200), dtype=np.uint8)
        template = np.zeros((30, 30), dtype=np.uint8)
        cv2.rectangle(template, (5, 5), (25, 25), 255, -1)
        template_path = os.path.join(self.temp_dir, "monitor_target.png")
        cv2.imwrite(template_path, template)

        # Place template at top_left x=50, y=50 -> local center x=65, y=65
        canvas[50:80, 50:80] = template
        # Set monitor offset as if secondary monitor is positioned at x=1920, y=0
        self.vision._monitor_offset = (1920, 0)

        match = self.vision.find_template(template_path, threshold=0.9, screen_gray=canvas)
        self.assertIsNotNone(match)
        self.assertEqual(match["x"], 1920 + 65)
        self.assertEqual(match["y"], 65)
        self.assertEqual(match["local_top_left"], (50, 50))


if __name__ == "__main__":
    unittest.main()
