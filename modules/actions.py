import sys
import types

# Preemptively mock mouseinfo to prevent mouseinfo's missing-tkinter sys.exit()
if "mouseinfo" not in sys.modules:
    dummy_mouseinfo = types.ModuleType("mouseinfo")
    dummy_mouseinfo.MouseInfoWindow = lambda *a, **k: None
    sys.modules["mouseinfo"] = dummy_mouseinfo

import random
import time
import pyautogui
import config

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
        """
        target_x = x + random.randint(-offset, offset)
        target_y = y + random.randint(-offset, offset)

        duration = random.uniform(config.MIN_CLICK_DURATION, config.MAX_CLICK_DURATION)
        pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeOutQuad)
        pyautogui.click()
        print(f"[ACTION] Clicked at ({target_x}, {target_y})")

    @staticmethod
    def click_match(match_result):
        """Convenience method to click a vision match object."""
        if match_result:
            ActionEngine.click_at(match_result['x'], match_result['y'])
            ActionEngine.human_delay()
            return True
        return False

    @staticmethod
    def navigate_to_url(url=config.DIRECT_TREASURE_URL):
        """
        Navigates browser directly to specified URL via Ctrl+L address bar input.
        """
        print(f"[ACTION] Navigating directly to URL: {url}")
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.5)
        pyautogui.write(url, interval=0.01)
        pyautogui.press('enter')
        ActionEngine.human_delay(5.0, 10.0)

    @staticmethod
    def refresh_page():
        """Performs browser page refresh or direct URL navigation."""
        if config.DIRECT_LANDING_MODE:
            ActionEngine.navigate_to_url(config.DIRECT_TREASURE_URL)
        else:
            print("[ACTION] Refreshing browser page (F5)...")
            pyautogui.press('f5')
            ActionEngine.human_delay(5.0, 10.0)
