import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
import types

# Preemptively mock mouseinfo to prevent mouseinfo's missing-tkinter sys.exit()
if "mouseinfo" not in sys.modules:
    dummy_mouseinfo = types.ModuleType("mouseinfo")
    dummy_mouseinfo.MouseInfoWindow = lambda *a, **k: None
    sys.modules["mouseinfo"] = dummy_mouseinfo

from modules.logger import logger

# Ensure DISPLAY environment variable is set on Linux before importing pyautogui
if sys.platform.startswith("linux") and "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":99"

try:
    import pyautogui
except Exception as pyauto_err:
    logger.warning(
        f"[ACTION] Could not initialize PyAutoGUI display connection ({pyauto_err}). Using headless dummy."
    )
    pyautogui = types.ModuleType("pyautogui")
    pyautogui.FAILSAFE = True
    pyautogui.moveTo = lambda *a, **k: None
    pyautogui.position = lambda *a, **k: (500, 500)
    pyautogui.mouseDown = lambda *a, **k: None
    pyautogui.mouseUp = lambda *a, **k: None
    pyautogui.press = lambda *a, **k: None
    pyautogui.write = lambda *a, **k: None
    pyautogui.hotkey = lambda *a, **k: None
    pyautogui.click = lambda *a, **k: None
    sys.modules["pyautogui"] = pyautogui

import config

try:
    from evdev import ecodes as e
except Exception:

    class DummyEcodes:
        EV_KEY = 1
        BTN_LEFT = 272
        BTN_RIGHT = 273

    e = DummyEcodes()

try:
    from evdev import UInput

    UINPUT_MOUSE = UInput({e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT]}, name="bombcrypto-uinput-mouse")
except Exception as uinput_err:
    UINPUT_MOUSE = None
    logger.debug(f"[ACTION] Notice: uinput mouse initialization note: {uinput_err}")


HAS_HYPRCTL = shutil.which("hyprctl") is not None


def get_hyprland_scale():
    """Queries Hyprland monitor display scale (e.g. 1.2 for 120% scale)."""
    if HAS_HYPRCTL:
        try:
            proc = subprocess.run(
                ["hyprctl", "monitors", "-j"], capture_output=True, text=True, timeout=2
            )
            monitors = json.loads(proc.stdout)
            if monitors and isinstance(monitors, list):
                return float(monitors[0].get("scale", 1.0))
        except Exception:
            pass
    return 1.0


# Enable PyAutoGUI fail-safe (moving mouse to any corner stops execution)
pyautogui.FAILSAFE = True


def generate_bezier_curve(start, end, num_points=15):
    """
    Generates a list of (x, y) tuples forming a cubic Bézier curve with human-like ease-in-out easing.
    """
    start_x, start_y = start
    end_x, end_y = end

    distance = math.hypot(end_x - start_x, end_y - start_y)
    if distance < 3 or num_points <= 2:
        return [start, end]

    # Vector from start to end
    vx = end_x - start_x
    vy = end_y - start_y

    # Perpendicular normal vector
    norm = math.hypot(vx, vy)
    if norm > 0:
        nx = -vy / norm
        ny = vx / norm
    else:
        nx, ny = 0, 0

    # Control points P1 and P2 offset randomly perpendicular to straight line path
    offset_scale = random.uniform(-0.25, 0.25) * distance
    p1 = (
        start_x + 0.3 * vx + offset_scale * nx,
        start_y + 0.3 * vy + offset_scale * ny,
    )
    p2 = (
        start_x + 0.7 * vx + offset_scale * nx,
        start_y + 0.7 * vy + offset_scale * ny,
    )

    points = []
    for i in range(num_points):
        u = i / float(num_points - 1)
        # Cosine ease-in-out for realistic acceleration & deceleration
        t = 0.5 * (1.0 - math.cos(math.pi * u))

        # Cubic Bézier formula
        one_minus_t = 1.0 - t
        t_sq = t * t
        t_cube = t_sq * t
        one_minus_t_sq = one_minus_t * one_minus_t
        one_minus_t_cube = one_minus_t_sq * one_minus_t

        x = (
            one_minus_t_cube * start_x
            + 3 * one_minus_t_sq * t * p1[0]
            + 3 * one_minus_t * t_sq * p2[0]
            + t_cube * end_x
        )
        y = (
            one_minus_t_cube * start_y
            + 3 * one_minus_t_sq * t * p1[1]
            + 3 * one_minus_t * t_sq * p2[1]
            + t_cube * end_y
        )
        points.append((int(round(x)), int(round(y))))

    return points


class ActionEngine:
    @staticmethod
    def move_mouse_bezier(start_x, start_y, end_x, end_y, duration=0.2, steps=None):
        """
        Moves mouse along a cubic Bézier curve from (start_x, start_y) to (end_x, end_y).
        """
        distance = math.hypot(end_x - start_x, end_y - start_y)
        if steps is None:
            min_steps = getattr(config, "BEZIER_MIN_STEPS", 5)
            steps = max(min_steps, int(distance / 15))

        points = generate_bezier_curve((start_x, start_y), (end_x, end_y), num_points=steps)
        step_delay = max(0.001, duration / float(len(points)))

        scale = get_hyprland_scale() if HAS_HYPRCTL else 1.0
        for pt_x, pt_y in points:
            if HAS_HYPRCTL:
                try:
                    logic_x = int(pt_x / scale)
                    logic_y = int(pt_y / scale)
                    subprocess.run(
                        ["hyprctl", "dispatch", "movecursor", str(logic_x), str(logic_y)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    pass
            try:
                pyautogui.moveTo(pt_x, pt_y)
            except Exception:
                pass
            time.sleep(step_delay)

    @staticmethod
    def human_delay(
        min_sec=config.MIN_ACTION_DELAY,
        max_sec=config.MAX_ACTION_DELAY,
        use_gaussian=None,
    ):
        """
        Waits a randomized human-like delay.
        Supports Gaussian (normal) distribution centered between min_sec and max_sec.
        """
        if use_gaussian is None:
            use_gaussian = getattr(config, "USE_GAUSSIAN_DELAYS", True)

        if use_gaussian:
            mu = (min_sec + max_sec) / 2.0
            sigma = (max_sec - min_sec) / 6.0
            delay = random.gauss(mu, sigma)
            delay = max(min_sec, min(max_sec, delay))
        else:
            delay = random.uniform(min_sec, max_sec)

        time.sleep(delay)
        return delay

    @staticmethod
    def idle_jitter(max_offset=None):
        """
        Performs periodic anti-AFK idle mouse movement by subtle jittering from current position.
        """
        if max_offset is None:
            max_offset = getattr(config, "IDLE_JITTER_MAX_OFFSET", 15)

        try:
            cur_x, cur_y = pyautogui.position()
        except Exception:
            cur_x, cur_y = 500, 500

        dx = random.choice([-1, 1]) * random.randint(3, max_offset)
        dy = random.choice([-1, 1]) * random.randint(3, max_offset)
        target_x = cur_x + dx
        target_y = cur_y + dy

        logger.info(
            f"[ACTION] Executing anti-AFK idle jitter: ({cur_x}, {cur_y}) -> ({target_x}, {target_y})"
        )
        if getattr(config, "DRY_RUN", False):
            logger.info(
                f"[DRY-RUN] [ACTION] Would perform anti-AFK idle jitter to ({target_x}, {target_y})"
            )
            return target_x, target_y

        ActionEngine.move_mouse_bezier(cur_x, cur_y, target_x, target_y, duration=0.15)
        return target_x, target_y

    @staticmethod
    def click_at(x, y, offset=config.MOUSE_CLICK_OFFSET):
        """
        Moves to (x, y) with slight random pixel variation and clicks.
        Uses non-linear Bézier trajectory and uinput kernel device for native clicking.
        """
        target_x = x + random.randint(-offset, offset)
        target_y = y + random.randint(-offset, offset)

        if getattr(config, "DRY_RUN", False):
            logger.info(f"[DRY-RUN] [ACTION] Would click at physical ({target_x}, {target_y})")
            return

        use_bezier = getattr(config, "USE_BEZIER_CURVES", True)
        if use_bezier:
            try:
                cur_x, cur_y = pyautogui.position()
            except Exception:
                cur_x, cur_y = target_x, target_y
            ActionEngine.move_mouse_bezier(cur_x, cur_y, target_x, target_y)
        else:
            if HAS_HYPRCTL:
                try:
                    scale = get_hyprland_scale()
                    logic_x = int(target_x / scale)
                    logic_y = int(target_y / scale)
                    subprocess.run(
                        ["hyprctl", "dispatch", "movecursor", str(logic_x), str(logic_y)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    time.sleep(0.15)
                except Exception:
                    pass

            try:
                pyautogui.moveTo(target_x, target_y)
            except Exception:
                pass

        # 2. Perform native kernel uinput click if available
        if UINPUT_MOUSE:
            try:
                UINPUT_MOUSE.write(e.EV_KEY, e.BTN_LEFT, 1)
                UINPUT_MOUSE.syn()
                time.sleep(0.10)
                UINPUT_MOUSE.write(e.EV_KEY, e.BTN_LEFT, 0)
                UINPUT_MOUSE.syn()
                logger.info(
                    f"[ACTION] Performed native kernel uinput click at physical ({target_x}, {target_y})"
                )
                return
            except Exception as err:
                logger.warning(f"[ACTION] uinput click failed ({err}). Falling back to pyautogui.")

        # Fallback to PyAutoGUI click
        pyautogui.mouseDown(button="left")
        time.sleep(0.10)
        pyautogui.mouseUp(button="left")
        logger.info(f"[ACTION] Moved cursor to physical ({target_x}, {target_y}) and clicked.")

    @staticmethod
    def click_match(match_result):
        """Convenience method to click a vision match object."""
        if match_result:
            ActionEngine.click_at(match_result["x"], match_result["y"])
            ActionEngine.human_delay()
            return True
        return False

    @staticmethod
    def navigate_to_url(url=config.DIRECT_TREASURE_URL):
        """
        Navigates browser directly to specified URL via Ctrl+L address bar input.
        """
        logger.info(f"[ACTION] Navigating directly to URL: {url}")
        if getattr(config, "DRY_RUN", False):
            logger.info(f"[DRY-RUN] [ACTION] Would navigate to URL: {url}")
            return

        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.5)
        pyautogui.write(url, interval=0.01)
        pyautogui.press("enter")
        ActionEngine.human_delay(5.0, 10.0)

    @staticmethod
    def refresh_page():
        """Performs browser page refresh or direct URL navigation."""
        if config.DIRECT_LANDING_MODE:
            ActionEngine.navigate_to_url(config.DIRECT_TREASURE_URL)
        else:
            logger.info("[ACTION] Refreshing browser page (F5)...")
            if getattr(config, "DRY_RUN", False):
                logger.info("[DRY-RUN] [ACTION] Would press F5 to refresh page")
                return

            pyautogui.press("f5")
            ActionEngine.human_delay(5.0, 10.0)
