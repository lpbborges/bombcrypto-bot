import io
import os
import shutil
import subprocess
import sys
import tempfile

import cv2
import mss
import numpy as np
from PIL import Image

import config
from modules.logger import logger


class VisionEngine:
    def __init__(self, monitor_index=config.SCREENSHOT_MONITOR_INDEX):
        self.monitor_index = monitor_index
        try:
            mss_factory = getattr(mss, "MSS", mss.mss)
            self.sct = mss_factory()
        except Exception as e:
            logger.warning(
                f"[VISION] Could not initialize mss screen capture connection ({e}). Display may be missing."
            )
            self.sct = None
        self.use_wayland_grim = self._check_wayland_grim()
        self._cached_screen = None
        self._template_cache = {}
        if self.use_wayland_grim:
            logger.info(
                "[VISION] Wayland environment detected. Using 'grim' for native screen capture."
            )

    def _check_wayland_grim(self):
        is_wayland = (
            "WAYLAND_DISPLAY" in os.environ or os.environ.get("XDG_SESSION_TYPE") == "wayland"
        )
        has_grim = shutil.which("grim") is not None
        return is_wayland and has_grim

    def clear_cache(self):
        """Invalidates the cached screen frame so the next capture will grab a fresh frame."""
        self._cached_screen = None

    def clear_template_cache(self):
        """Clears cached template images."""
        self._template_cache.clear()

    def _load_template(self, template_path):
        """Loads and caches a grayscale template image."""
        if not template_path or not os.path.exists(template_path):
            return None
        if template_path in self._template_cache:
            return self._template_cache[template_path]
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is not None:
            self._template_cache[template_path] = template
        return template

    def _capture_via_grim(self):
        """Captures screen using native Wayland tool 'grim'."""
        try:
            proc = subprocess.Popen(
                ["grim", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            stdout, _ = proc.communicate()
            if stdout:
                img = Image.open(io.BytesIO(stdout))
                img_np = np.array(img)
                if img_np.ndim == 3:
                    if img_np.shape[2] == 4:
                        return cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
                    elif img_np.shape[2] == 3:
                        return cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                return img_np
        except Exception as e:
            logger.warning(f"[VISION] grim screen capture failed: {e}")
        return None

    def _capture_via_mss(self):
        """Attempts screen capture using mss with monitor bounds checking and error handling."""
        if self.sct is None:
            try:
                mss_factory = getattr(mss, "MSS", mss.mss)
                self.sct = mss_factory()
            except Exception as e:
                logger.warning(
                    f"[VISION] Could not initialize mss screen capture connection ({e})."
                )
                return None

        if self.sct is None:
            return None

        try:
            monitors = getattr(self.sct, "monitors", [])
        except Exception as e:
            logger.warning(f"[VISION] Failed to access mss monitors: {e}")
            return None

        if not monitors:
            return None

        num_monitors = len(monitors)
        monitors_to_try = []

        # Target requested monitor index first if valid
        if 0 <= self.monitor_index < num_monitors:
            monitors_to_try.append(self.monitor_index)

        # Fallback monitor indices: 0 (all combined) and 1 (primary)
        for idx in [0, 1]:
            if idx < num_monitors and idx not in monitors_to_try:
                monitors_to_try.append(idx)

        for idx in monitors_to_try:
            try:
                monitor = monitors[idx]
                sct_img = self.sct.grab(monitor)
                img_np = np.array(sct_img)

                # Check if mss returned pure black screen (Wayland X11 restriction)
                if img_np.max() == 0 and shutil.which("grim"):
                    logger.warning(
                        "[VISION] mss returned black screenshot (Wayland X11 restriction). Enabling grim."
                    )
                    self.use_wayland_grim = True
                    return None

                if img_np.size > 0:
                    return cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
            except Exception as e:
                logger.warning(
                    f"[VISION] mss grab failed for monitor index {idx} ({type(e).__name__}: {e})."
                )

        return None

    def _capture_via_pil_imagegrab(self):
        """Attempts screen capture using PIL ImageGrab."""
        try:
            from PIL import ImageGrab

            pil_img = ImageGrab.grab()
            if pil_img is not None:
                img_np = np.array(pil_img)
                if img_np.ndim == 3:
                    if img_np.shape[2] == 4:
                        return cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
                    elif img_np.shape[2] == 3:
                        return cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                return img_np
        except Exception as e:
            logger.warning(f"[VISION] PIL ImageGrab screen capture failed: {e}")
        return None

    def _capture_via_cli_utils(self):
        """Attempts screen capture using CLI utilities like gnome-screenshot or scrot."""
        for tool, cmd in [
            ("gnome-screenshot", ["gnome-screenshot", "-f"]),
            ("scrot", ["scrot"]),
        ]:
            if shutil.which(tool):
                tmp_path = os.path.join(tempfile.gettempdir(), f"bot_screen_{tool}.png")
                try:
                    res = subprocess.run(cmd + [tmp_path], capture_output=True, timeout=5)
                    if res.returncode == 0 and os.path.exists(tmp_path):
                        img_np = cv2.imread(tmp_path, cv2.IMREAD_GRAYSCALE)
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                        if img_np is not None and img_np.size > 0:
                            return img_np
                except Exception as e:
                    logger.warning(f"[VISION] CLI screenshot tool '{tool}' failed: {e}")
        return None

    def capture_screen(self, force_refresh=False):
        """
        Captures the screen and returns a grayscale numpy array.
        Supports Wayland (grim), X11 (mss with monitor fallbacks), PIL ImageGrab, and CLI tools.
        Saves debug_last_screen.png.
        """
        if not force_refresh and self._cached_screen is not None:
            return self._cached_screen

        gray_img = None

        # 1. Primary Wayland capture via grim if enabled
        if self.use_wayland_grim:
            gray_img = self._capture_via_grim()

        # 2. Capture via MSS (X11 / Xwayland) with error and bounds handling
        if gray_img is None:
            try:
                gray_img = self._capture_via_mss()
            except Exception as e:
                logger.warning(f"[VISION] _capture_via_mss error: {e}")

        # 3. Fallback to grim if mss failed and grim exists
        if gray_img is None and shutil.which("grim"):
            gray_img = self._capture_via_grim()

        # 4. Fallback to PIL ImageGrab
        if gray_img is None:
            gray_img = self._capture_via_pil_imagegrab()

        # 5. Fallback to CLI screenshot tools (gnome-screenshot, scrot)
        if gray_img is None:
            gray_img = self._capture_via_cli_utils()

        # 6. Fallback if all screen capture methods failed
        if gray_img is None:
            is_wayland_no_grim = (
                sys.platform.startswith("linux")
                and (
                    "WAYLAND_DISPLAY" in os.environ
                    or os.environ.get("XDG_SESSION_TYPE") == "wayland"
                )
                and shutil.which("grim") is None
            )
            if is_wayland_no_grim:
                logger.error(
                    "[VISION] All screen capture methods failed. Wayland environment detected without 'grim'. "
                    "Please install 'grim' (`sudo apt install grim`) or set SCREENSHOT_MONITOR_INDEX = 0 in config.py / .env."
                )
            else:
                logger.error(
                    "[VISION] All screen capture methods failed. "
                    "Please check display connection or set SCREENSHOT_MONITOR_INDEX = 0 in config.py / .env."
                )
            gray_img = np.zeros((1080, 1920), dtype=np.uint8)

        self._cached_screen = gray_img

        if config.SAVE_DEBUG_IMAGES and gray_img is not None:
            debug_path = os.path.join(config.DEBUG_DIR, "debug_last_screen.png")
            cv2.imwrite(debug_path, gray_img)

        return gray_img

    def save_debug_match(self, template_name, match_result, screen_gray=None):
        """
        Draws a bounding box and label over the matched target and saves debug_last_match.png.
        """
        if not config.SAVE_DEBUG_IMAGES or not match_result:
            return

        if screen_gray is None:
            screen_gray = self.capture_screen()

        debug_img = cv2.cvtColor(screen_gray, cv2.COLOR_GRAY2BGR)
        top_left = match_result["top_left"]
        w, h = match_result["w"], match_result["h"]
        bottom_right = (top_left[0] + w, top_left[1] + h)

        # Draw green bounding box rectangle
        cv2.rectangle(debug_img, top_left, bottom_right, (0, 255, 0), 3)

        # Draw text label
        label = f"{template_name} ({match_result['confidence']:.2f})"
        cv2.putText(
            debug_img,
            label,
            (top_left[0], max(20, top_left[1] - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        match_path = os.path.join(config.DEBUG_DIR, "debug_last_match.png")
        cv2.imwrite(match_path, debug_img)
        logger.debug(f"[VISION DEBUG] Saved match visualization to: {match_path}")

    def _crop_roi(self, screen_gray, roi):
        """
        Crops screen_gray based on ROI specification.
        ROI can be:
        - (ymin, xmin, ymax, xmax) floats 0.0-1.0 (normalized screen coords)
        - (x, y, w, h) integers (pixel bounds)
        Returns: (cropped_img, offset_x, offset_y)
        """
        if roi is None:
            return screen_gray, 0, 0

        h_scr, w_scr = screen_gray.shape[:2]
        if len(roi) == 4:
            if all(
                isinstance(v, float) or (isinstance(v, (int, float)) and 0.0 <= v <= 1.0)
                for v in roi
            ):
                # Normalized coordinates (ymin, xmin, ymax, xmax)
                ymin = int(roi[0] * h_scr)
                xmin = int(roi[1] * w_scr)
                ymax = int(roi[2] * h_scr)
                xmax = int(roi[3] * w_scr)
            else:
                # Pixel coordinates (x, y, w, h)
                xmin = int(roi[0])
                ymin = int(roi[1])
                xmax = xmin + int(roi[2])
                ymax = ymin + int(roi[3])

            # Clamp bounds to screen dimensions
            xmin = max(0, min(xmin, w_scr - 1))
            ymin = max(0, min(ymin, h_scr - 1))
            xmax = max(xmin + 1, min(xmax, w_scr))
            ymax = max(ymin + 1, min(ymax, h_scr))

            return screen_gray[ymin:ymax, xmin:xmax], xmin, ymin

        return screen_gray, 0, 0

    def find_template(self, template_path, threshold=None, screen_gray=None, roi=None):
        """
        Locates template image on screen using multi-scale OpenCV template matching.
        Supports Region of Interest (ROI) bounding and target-specific thresholds.

        Returns:
            dict: { 'x': int, 'y': int, 'w': int, 'h': int, 'confidence': float, 'top_left': tuple } or None
        """
        if not os.path.exists(template_path):
            return None

        if threshold is None:
            threshold = config.get_target_threshold(template_path)

        if roi is None:
            roi = config.get_target_roi(template_path)

        if screen_gray is None:
            screen_gray = self.capture_screen()

        template = self._load_template(template_path)
        if template is None:
            return None

        orig_h, orig_w = template.shape[:2]
        search_gray, offset_x, offset_y = self._crop_roi(screen_gray, roi)

        best_val = -1.0
        best_match = None

        # Test multi-scale matches from 0.70x to 1.30x scaling
        scales = [1.0, 0.90, 1.10, 0.80, 1.20, 0.70, 1.30]
        for scale in scales:
            w, h = int(orig_w * scale), int(orig_h * scale)
            if w < 10 or h < 10 or w > search_gray.shape[1] or h > search_gray.shape[0]:
                continue

            resized_temp = (
                cv2.resize(template, (w, h), interpolation=cv2.INTER_AREA)
                if scale < 1.0
                else cv2.resize(template, (w, h), interpolation=cv2.INTER_CUBIC)
            )
            res = cv2.matchTemplate(search_gray, resized_temp, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val > best_val:
                best_val = max_val
                best_match = {
                    "x": max_loc[0] + offset_x + w // 2,
                    "y": max_loc[1] + offset_y + h // 2,
                    "w": w,
                    "h": h,
                    "top_left": (max_loc[0] + offset_x, max_loc[1] + offset_y),
                    "confidence": float(max_val),
                    "scale": scale,
                }

        if best_match and best_match["confidence"] >= threshold:
            template_name = os.path.basename(template_path)
            self.save_debug_match(template_name, best_match, screen_gray)
            return best_match

        return None

    def find_all_templates(self, template_path, threshold=None, screen_gray=None, roi=None):
        """
        Finds all occurrences of template image on screen above the threshold (with ROI support).
        """
        if not os.path.exists(template_path):
            return []

        if threshold is None:
            threshold = config.get_target_threshold(template_path)

        if roi is None:
            roi = config.get_target_roi(template_path)

        if screen_gray is None:
            screen_gray = self.capture_screen()

        template = self._load_template(template_path)
        if template is None:
            return []

        h, w = template.shape[:2]
        search_gray, offset_x, offset_y = self._crop_roi(screen_gray, roi)

        if w > search_gray.shape[1] or h > search_gray.shape[0]:
            return []

        res = cv2.matchTemplate(search_gray, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(res >= threshold)

        matches = []
        for pt in zip(*locations[::-1]):
            matches.append(
                {
                    "x": pt[0] + offset_x + w // 2,
                    "y": pt[1] + offset_y + h // 2,
                    "w": w,
                    "h": h,
                    "top_left": (pt[0] + offset_x, pt[1] + offset_y),
                    "confidence": float(res[pt[1], pt[0]]),
                }
            )
        return matches
