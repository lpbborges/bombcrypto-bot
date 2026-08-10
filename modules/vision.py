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
        Supports Wayland (grim) and X11 (mss). Saves debug_last_screen.png.
        """
        gray_img = None
        if self.use_wayland_grim:
            try:
                proc = subprocess.Popen(["grim", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                stdout, _ = proc.communicate()
                img = Image.open(io.BytesIO(stdout))
                img_np = np.array(img)
                if img_np.ndim == 3:
                    if img_np.shape[2] == 4:
                        gray_img = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
                    elif img_np.shape[2] == 3:
                        gray_img = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                else:
                    gray_img = img_np
            except Exception as e:
                print(f"[VISION] Warning: grim screen capture failed: {e}. Falling back to mss.")

        if gray_img is None:
            monitor = self.sct.monitors[self.monitor_index]
            sct_img = self.sct.grab(monitor)
            img_np = np.array(sct_img)
            # Check if mss returned pure black screen (Wayland X11 restriction)
            if img_np.max() == 0 and shutil.which("grim"):
                self.use_wayland_grim = True
                return self.capture_screen()
            gray_img = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)

        if config.SAVE_DEBUG_IMAGES and gray_img is not None:
            debug_path = os.path.join(config.BASE_DIR, "debug_last_screen.png")
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
        top_left = match_result['top_left']
        w, h = match_result['w'], match_result['h']
        bottom_right = (top_left[0] + w, top_left[1] + h)

        # Draw green bounding box rectangle
        cv2.rectangle(debug_img, top_left, bottom_right, (0, 255, 0), 3)

        # Draw text label
        label = f"{template_name} ({match_result['confidence']:.2f})"
        cv2.putText(debug_img, label, (top_left[0], max(20, top_left[1] - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        match_path = os.path.join(config.BASE_DIR, "debug_last_match.png")
        cv2.imwrite(match_path, debug_img)
        print(f"[VISION DEBUG] Saved match visualization to: {match_path}")

    def find_template(self, template_path, threshold=config.DEFAULT_MATCH_THRESHOLD, screen_gray=None):
        """
        Locates template image on screen using multi-scale OpenCV template matching.
        
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

        orig_h, orig_w = template.shape[:2]

        best_val = -1.0
        best_match = None

        # Test multi-scale matches from 0.70x to 1.30x scaling
        scales = [1.0, 0.90, 1.10, 0.80, 1.20, 0.70, 1.30]
        for scale in scales:
            w, h = int(orig_w * scale), int(orig_h * scale)
            if w < 10 or h < 10 or w > screen_gray.shape[1] or h > screen_gray.shape[0]:
                continue

            resized_temp = cv2.resize(template, (w, h), interpolation=cv2.INTER_AREA) if scale < 1.0 else cv2.resize(template, (w, h), interpolation=cv2.INTER_CUBIC)
            res = cv2.matchTemplate(screen_gray, resized_temp, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val > best_val:
                best_val = max_val
                best_match = {
                    'x': max_loc[0] + w // 2,
                    'y': max_loc[1] + h // 2,
                    'w': w,
                    'h': h,
                    'top_left': max_loc,
                    'confidence': float(max_val),
                    'scale': scale
                }

        if best_match and best_match['confidence'] >= threshold:
            template_name = os.path.basename(template_path)
            self.save_debug_match(template_name, best_match, screen_gray)
            return best_match

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
