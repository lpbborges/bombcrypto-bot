import sys
import types

# Preemptively mock mouseinfo to prevent mouseinfo's missing-tkinter sys.exit()
if "mouseinfo" not in sys.modules:
    dummy_mouseinfo = types.ModuleType("mouseinfo")
    dummy_mouseinfo.MouseInfoWindow = lambda *a, **k: None
    sys.modules["mouseinfo"] = dummy_mouseinfo

import json
import random
import shutil
import subprocess
import time

import pyautogui

import config

try:
    from evdev import UInput
    from evdev import ecodes as e

    UINPUT_MOUSE = UInput({e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT]}, name="bombcrypto-uinput-mouse")
except Exception as uinput_err:
    UINPUT_MOUSE = None
    print(f"[ACTION] Notice: uinput mouse initialization note: {uinput_err}")

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


class ActionEngine:
    @staticmethod
    def human_delay(min_sec=config.MIN_ACTION_DELAY, max_sec=config.MAX_ACTION_DELAY):
        """Waits a randomized human-like delay."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    @staticmethod
    def click_at(x, y, offset=config.MOUSE_CLICK_OFFSET):
        """
        Moves to (x, y) with slight random pixel variation and clicks.
        Uses uinput kernel device for 100% native hardware clicking under Wayland/Hyprland.
        """
        target_x = x + random.randint(-offset, offset)
        target_y = y + random.randint(-offset, offset)

        # 1. Position hardware cursor via Hyprland hyprctl
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
                print(
                    f"[ACTION] Performed native kernel uinput click at physical ({target_x}, {target_y})"
                )
                return
            except Exception as err:
                print(f"[ACTION] Warning: uinput click failed ({err}). Falling back to pyautogui.")

        # Fallback to PyAutoGUI click
        pyautogui.mouseDown(button="left")
        time.sleep(0.10)
        pyautogui.mouseUp(button="left")
        print(f"[ACTION] Moved cursor to physical ({target_x}, {target_y}) and clicked.")

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
        print(f"[ACTION] Navigating directly to URL: {url}")
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
            print("[ACTION] Refreshing browser page (F5)...")
            pyautogui.press("f5")
            ActionEngine.human_delay(5.0, 10.0)
