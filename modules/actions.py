from __future__ import annotations

import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
import types

from config import BotConfig
from modules import ensure_mouseinfo_mocked, platform_utils
from modules.logger import logger

ensure_mouseinfo_mocked()

# Ensure DISPLAY environment variable is set on Linux before importing pyautogui
if platform_utils.is_linux() and "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":0"

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


try:
    from evdev import ecodes
except Exception:

    class DummyEcodes:
        EV_KEY = 1
        BTN_LEFT = 272
        BTN_RIGHT = 273

    ecodes = DummyEcodes()

try:
    from evdev import UInput

    UINPUT_MOUSE = UInput(
        {ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT]}, name="bombcrypto-uinput-mouse"
    )
except Exception as uinput_err:
    UINPUT_MOUSE = None
    logger.debug(f"[ACTION] Notice: uinput mouse initialization note: {uinput_err}")

HAS_HYPRCTL = shutil.which("hyprctl") is not None
HAS_YDOTOOL = shutil.which("ydotool") is not None
HAS_XDOTOOL = shutil.which("xdotool") is not None


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
        except Exception as e:
            logger.debug(f"Exception caught: {e}", exc_info=True)
    return 1.0


# Enable PyAutoGUI fail-safe (moving mouse to any corner stops execution)
try:
    pyautogui.FAILSAFE = True
except Exception:
    pass


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
    def __init__(self, cfg: BotConfig):
        self.config = cfg

    def move_mouse_bezier(self, start_x, start_y, end_x, end_y, duration=None, steps=None):
        """
        Moves mouse along a cubic Bézier curve from (start_x, start_y) to (end_x, end_y).
        """
        if duration is None:
            min_dur = getattr(self.config, "min_click_duration", 0.08)
            max_dur = getattr(self.config, "max_click_duration", 0.20)
            duration = random.uniform(min_dur, max_dur)

        distance = math.hypot(end_x - start_x, end_y - start_y)
        if steps is None:
            min_steps = getattr(self.config, "bezier_min_steps", 5)
            steps = max(min_steps, int(distance / 25))

        points = generate_bezier_curve((start_x, start_y), (end_x, end_y), num_points=steps)
        step_delay = max(0.0005, duration / float(len(points)))

        scale = get_hyprland_scale() if HAS_HYPRCTL else 1.0
        for pt_x, pt_y in points:
            try:
                pyautogui.moveTo(pt_x, pt_y)
            except Exception as e:
                logger.debug(f"Exception caught: {e}", exc_info=True)
            time.sleep(step_delay)

        if HAS_HYPRCTL:
            try:
                logic_x = int(end_x / scale)
                logic_y = int(end_y / scale)
                subprocess.run(
                    ["hyprctl", "dispatch", "movecursor", str(logic_x), str(logic_y)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
            except Exception as e:
                logger.debug(f"Exception caught: {e}", exc_info=True)

    def human_delay(
        self,
        min_sec=None,
        max_sec=None,
        use_gaussian=None,
    ):
        """
        Waits a randomized human-like delay.
        Supports Gaussian (normal) distribution centered between min_sec and max_sec.
        """
        if min_sec is None:
            min_sec = self.config.min_action_delay
        if max_sec is None:
            max_sec = self.config.max_action_delay
        if use_gaussian is None:
            use_gaussian = getattr(self.config, "use_gaussian_delays", True)

        if use_gaussian:
            mu = (min_sec + max_sec) / 2.0
            sigma = (max_sec - min_sec) / 6.0
            delay = random.gauss(mu, sigma)
            delay = max(min_sec, min(max_sec, delay))
        else:
            delay = random.uniform(min_sec, max_sec)

        time.sleep(delay)
        return delay

    def idle_jitter(self, max_offset=None):
        """
        Performs periodic anti-AFK idle mouse movement by subtle jittering from current position.
        """
        if max_offset is None:
            max_offset = getattr(self.config, "idle_jitter_max_offset", 15)

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
        if getattr(self.config, "dry_run", False):
            logger.info(
                f"[DRY-RUN] [ACTION] Would perform anti-AFK idle jitter to ({target_x}, {target_y})"
            )
            return target_x, target_y

        self.move_mouse_bezier(cur_x, cur_y, target_x, target_y, duration=0.10)
        return target_x, target_y

    def click_at(self, x, y, offset=None):
        """
        Moves to (x, y) with slight random pixel variation and clicks.
        Supports Bézier trajectory, kernel uinput device, ydotool (Wayland), xdotool (X11), and PyAutoGUI.
        """
        target_x = x + random.randint(-offset, offset)
        target_y = y + random.randint(-offset, offset)

        if getattr(self.config, "dry_run", False):
            logger.info(f"[DRY-RUN] [ACTION] Would click at physical ({target_x}, {target_y})")
            return

        use_bezier = getattr(self.config, "use_bezier_curves", True)
        if use_bezier:
            try:
                cur_x, cur_y = pyautogui.position()
            except Exception:
                cur_x, cur_y = target_x, target_y
            self.move_mouse_bezier(cur_x, cur_y, target_x, target_y)
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
                        timeout=2,
                    )
                    time.sleep(0.05)
                except Exception as e:
                    logger.debug(f"Exception caught: {e}", exc_info=True)

            try:
                pyautogui.moveTo(target_x, target_y)
            except Exception as e:
                logger.debug(f"Exception caught: {e}", exc_info=True)

        # 1. Perform native kernel uinput click if available
        if UINPUT_MOUSE:
            try:
                UINPUT_MOUSE.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1)
                UINPUT_MOUSE.syn()
                time.sleep(0.04)
                UINPUT_MOUSE.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
                UINPUT_MOUSE.syn()
                logger.info(
                    f"[ACTION] Performed native kernel uinput click at physical ({target_x}, {target_y})"
                )
                return
            except Exception as err:
                logger.warning(f"[ACTION] uinput click failed ({err}). Falling back...")

        # 2. Perform ydotool click (Linux Wayland fallback)
        if HAS_YDOTOOL:
            try:
                subprocess.run(
                    ["ydotool", "mousemove", "-a", str(target_x), str(target_y)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                subprocess.run(
                    ["ydotool", "click", "0xC0"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                logger.info(
                    f"[ACTION] Performed ydotool click at physical ({target_x}, {target_y})"
                )
                return
            except Exception as err:
                logger.debug(f"[ACTION] ydotool click notice: {err}")

        # 3. Perform xdotool click (Linux X11 fallback)
        if HAS_XDOTOOL:
            try:
                subprocess.run(
                    ["xdotool", "mousemove", str(target_x), str(target_y), "click", "1"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                logger.info(
                    f"[ACTION] Performed xdotool click at physical ({target_x}, {target_y})"
                )
                return
            except Exception as err:
                logger.debug(f"[ACTION] xdotool click notice: {err}")

        # 4. Fallback to PyAutoGUI click
        try:
            pyautogui.mouseDown(button="left")
            time.sleep(0.04)
            pyautogui.mouseUp(button="left")
            logger.info(f"[ACTION] Moved cursor to physical ({target_x}, {target_y}) and clicked.")
        except Exception as err:
            logger.error(f"[ACTION] All mouse click methods failed: {err}")

    def click_match(self, match_result):
        """Convenience method to click a vision match object."""
        if match_result:
            ActionEngine.click_at(match_result["x"], match_result["y"])
            ActionEngine.human_delay()
            return True
        return False

    def navigate_to_url(self, url=None):
        """
        Navigates browser directly to specified URL via Ctrl+L address bar input.
        """
        logger.info(f"[ACTION] Navigating directly to URL: {url}")
        if getattr(self.config, "dry_run", False):
            logger.info(f"[DRY-RUN] [ACTION] Would navigate to URL: {url}")
            return

        try:
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.5)
            pyautogui.write(url, interval=0.01)
            pyautogui.press("enter")
        except Exception as err:
            logger.warning(f"[ACTION] hotkey URL navigation failed ({err}).")
        ActionEngine.human_delay(5.0, 10.0)

    def refresh_page(
        self,
    ):
        """Performs browser page refresh or direct URL navigation."""
        if self.config.direct_landing_mode:
            ActionEngine.navigate_to_url(self.config.direct_treasure_url)
        else:
            logger.info("[ACTION] Refreshing browser page (F5)...")
            if getattr(self.config, "dry_run", False):
                logger.info("[DRY-RUN] [ACTION] Would press F5 to refresh page")
                return

            try:
                pyautogui.press("f5")
            except Exception as err:
                logger.warning(f"[ACTION] F5 refresh failed ({err}).")
            ActionEngine.human_delay(5.0, 10.0)

    def drag_scroll(self, start_x, start_y, end_x, end_y, duration=0.35):
        """
        Performs mouse press, drag from (start_x, start_y) to (end_x, end_y), and release.
        Provides drag-scrolling for Unity/HTML5 UI containers (like Bombcrypto modals).
        Handles Hyprland display scale factor (e.g. 1.2x) and native display dispatching.
        """
        if getattr(self.config, "dry_run", False):
            logger.info(
                f"[DRY-RUN] [ACTION] Would drag-scroll from ({start_x}, {start_y}) to ({end_x}, {end_y})"
            )
            return

        logger.info(
            f"[ACTION] Executing modal drag-scroll: ({start_x}, {start_y}) -> ({end_x}, {end_y})"
        )

        scale = get_hyprland_scale() if HAS_HYPRCTL else 1.0

        # Convert physical screen coordinates to Hyprland logical coordinates
        logic_start_x = int(start_x / scale)
        logic_start_y = int(start_y / scale)
        logic_end_x = int(end_x / scale)
        logic_end_y = int(end_y / scale)

        # 1. Native Hyprland dispatch drag (Linux Wayland)
        if HAS_HYPRCTL:
            try:
                # Move cursor to logical start position
                subprocess.run(
                    ["hyprctl", "dispatch", "movecursor", str(logic_start_x), str(logic_start_y)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                time.sleep(0.06)

                # Press left mouse button down
                if UINPUT_MOUSE:
                    UINPUT_MOUSE.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1)
                    UINPUT_MOUSE.syn()
                else:
                    pyautogui.mouseDown(button="left")

                time.sleep(0.06)

                # Interpolate move steps from start to end
                steps = 15
                for i in range(1, steps + 1):
                    cur_lx = int(logic_start_x + (logic_end_x - logic_start_x) * (i / steps))
                    cur_ly = int(logic_start_y + (logic_end_y - logic_start_y) * (i / steps))
                    subprocess.run(
                        ["hyprctl", "dispatch", "movecursor", str(cur_lx), str(cur_ly)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2,
                    )
                    time.sleep(max(0.01, duration / steps))

                time.sleep(0.06)

                # Release left mouse button
                if UINPUT_MOUSE:
                    UINPUT_MOUSE.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
                    UINPUT_MOUSE.syn()
                else:
                    pyautogui.mouseUp(button="left")

                return
            except Exception as err:
                logger.debug(f"[ACTION] Hyprland drag-scroll notice: {err}")

        # 2. Native kernel uinput drag
        if UINPUT_MOUSE:
            try:
                self.move_mouse_bezier(start_x, start_y, start_x, start_y, duration=0.05)
                UINPUT_MOUSE.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 1)
                UINPUT_MOUSE.syn()
                time.sleep(0.05)
                self.move_mouse_bezier(start_x, start_y, end_x, end_y, duration=duration)
                time.sleep(0.05)
                UINPUT_MOUSE.write(ecodes.EV_KEY, ecodes.BTN_LEFT, 0)
                UINPUT_MOUSE.syn()
                return
            except Exception as err:
                logger.debug(f"[ACTION] uinput drag-scroll notice: {err}")

        # 3. xdotool drag (Linux X11)
        if HAS_XDOTOOL:
            try:
                subprocess.run(
                    [
                        "xdotool",
                        "mousemove",
                        str(start_x),
                        str(start_y),
                        "mousedown",
                        "1",
                        "mousemove",
                        str(end_x),
                        str(end_y),
                        "mouseup",
                        "1",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                return
            except Exception as err:
                logger.debug(f"[ACTION] xdotool drag-scroll notice: {err}")

        # 4. PyAutoGUI drag fallback
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=duration, button="left")
        except Exception as err:
            logger.error(f"[ACTION] PyAutoGUI drag-scroll failed: {err}")

    def scroll_down(self, x=None, y=None, distance=300, clicks=5):
        """
        Scrolls down the UI modal by performing a click-and-drag UP gesture inside the container,
        which scrolls the container content down in Bombcrypto and Unity web modals.
        """
        if getattr(self.config, "dry_run", False):
            logger.info(f"[DRY-RUN] [ACTION] Would scroll down modal at ({x}, {y})")
            return

        if x is None or y is None:
            try:
                cur_x, cur_y = pyautogui.position()
                x, y = cur_x, cur_y
            except Exception:
                x, y = 960, 540

        start_x = x
        start_y = y + int(distance / 2)
        end_x = x
        end_y = max(50, y - int(distance / 2))

        # Perform drag UP inside modal to scroll container content DOWN
        self.drag_scroll(start_x, start_y, end_x, end_y, duration=0.4)

        # Secondary wheel scroll attempt
        try:
            pyautogui.scroll(-int(clicks))
        except Exception as e:
            logger.debug(f"Exception caught: {e}", exc_info=True)

    def scroll_up(self, x=None, y=None, distance=300, clicks=5):
        """
        Scrolls up the UI modal by performing a click-and-drag DOWN gesture inside the container,
        which scrolls the container content up in Bombcrypto and Unity web modals.
        """
        if getattr(self.config, "dry_run", False):
            logger.info(f"[DRY-RUN] [ACTION] Would scroll up modal at ({x}, {y})")
            return

        if x is None or y is None:
            try:
                cur_x, cur_y = pyautogui.position()
                x, y = cur_x, cur_y
            except Exception:
                x, y = 960, 540

        start_x = x
        start_y = max(50, y - int(distance / 2))
        end_x = x
        end_y = y + int(distance / 2)

        # Perform drag DOWN inside modal to scroll container content UP
        self.drag_scroll(start_x, start_y, end_x, end_y, duration=0.4)

        # Secondary wheel scroll attempt
        try:
            pyautogui.scroll(int(clicks))
        except Exception as e:
            logger.debug(f"Exception caught: {e}", exc_info=True)
