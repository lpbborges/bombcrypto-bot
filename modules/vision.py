import os
import shutil
import subprocess
import cv2
import numpy as np
import mss
from PIL import Image
import io
import config

class VisionEngine:
    def __init__(self, monitor_index=config.SCREENSHOT_MONITOR_INDEX):
        self.monitor_index = monitor_index
        self.sct = mss.mss()
        self.use_wayland_grim = self._check_wayland_grim()
        if self.use_wayland_grim:
            print("[VISION] Wayland environment detected. Using 'grim' for native screen capture.")

    def _check_wayland_grim(self):
        is_wayland = "WAYLAND_DISPLAY" in os.environ or os.environ.get("XDG_SESSION_TYPE") == "wayland"
        has_grim = shutil.which("grim") is not None
        return is_wayland and has_grim

    def capture_screen(self):
        """
        Captures the screen and returns a grayscale numpy array.
        Supports Wayland (grim) and X11 (mss).
        """
        if self.use_wayland_grim:
            try:
                proc = subprocess.Popen(["grim", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                stdout, _ = proc.communicate()
                img = Image.open(io.BytesIO(stdout))
                img_np = np.array(img)
                if img_np.ndim == 3:
                    if img_np.shape[2] == 4:
                        return cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
                    elif img_np.shape[2] == 3:
                        return cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                return img_np
            except Exception as e:
                print(f"[VISION] Warning: grim screen capture failed: {e}. Falling back to mss.")

        monitor = self.sct.monitors[self.monitor_index]
        sct_img = self.sct.grab(monitor)
        img_np = np.array(sct_img)

        # Check if mss returned pure black screen (Wayland X11 restriction)
        if img_np.max() == 0 and shutil.which("grim"):
            self.use_wayland_grim = True
            return self.capture_screen()

        return cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)

    def find_template(self, template_path, threshold=config.DEFAULT_MATCH_THRESHOLD, screen_gray=None):
        """
        Locates template image on screen using OpenCV template matching.
        
        Returns:
            dict: { 'x': int, 'y': int, 'w': int, 'h': int, 'confidence': float } or None
        """
        if not os.path.exists(template_path):
            return None

        if screen_gray is None:
            screen_gray = self.capture_screen()

        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            return None

        h, w = template.shape[:2]

        # Execute template matching
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            top_left = max_loc
            center_x = top_left[0] + w // 2
            center_y = top_left[1] + h // 2
            return {
                'x': center_x,
                'y': center_y,
                'w': w,
                'h': h,
                'top_left': top_left,
                'confidence': float(max_val)
            }

        return None

    def find_all_templates(self, template_path, threshold=config.DEFAULT_MATCH_THRESHOLD, screen_gray=None):
        """
        Finds all occurrences of template image on screen above the threshold.
        """
        if not os.path.exists(template_path):
            return []

        if screen_gray is None:
            screen_gray = self.capture_screen()

        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            return []

        h, w = template.shape[:2]
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(res >= threshold)

        matches = []
        for pt in zip(*locations[::-1]):
            matches.append({
                'x': pt[0] + w // 2,
                'y': pt[1] + h // 2,
                'w': w,
                'h': h,
                'confidence': float(res[pt[1], pt[0]])
            })
        return matches
