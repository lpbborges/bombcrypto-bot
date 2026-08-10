import os
import sys
import time
import types

# Preemptively mock mouseinfo to prevent mouseinfo's missing-tkinter sys.exit()
if "mouseinfo" not in sys.modules:
    dummy_mouseinfo = types.ModuleType("mouseinfo")
    dummy_mouseinfo.MouseInfoWindow = lambda *a, **k: None
    sys.modules["mouseinfo"] = dummy_mouseinfo

# Add local path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from modules.bot_logic import BombCryptoBot
from modules.browser import BraveManager


class Logger:
    def __init__(self, filename=config.LOG_FILE_PATH):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()


sys.stdout = Logger()


def main():
    browser_info = BraveManager.get_attached_browser_info()

    print("==================================================")
    print("           BOMB CRYPTO AUTOMATION BOT             ")
    print("==================================================")
    print(" [ATTACHED BROWSER INFO]")
    print(f"  • Name:       {browser_info['name']}")
    print(f"  • Process ID: PID {browser_info['pid']}")
    print(f"  • Binary Exe: {browser_info['exe']}")
    print(f"  • Status:     {browser_info['status']}")
    print("--------------------------------------------------")
    print(f"  • Direct URL: {config.DIRECT_TREASURE_URL}")
    print(f"  • Interval:   {config.HERO_WORK_INTERVAL_MINUTES} minutes hero work cycle")
    print(f"  • Targets:    {config.TARGETS_DIR}")
    print("==================================================")
    print("Press Ctrl+C or move mouse to screen corner to exit.\n")

    # Verify Brave browser status
    if config.AUTO_LAUNCH_BRAVE:
        BraveManager.verify_and_ensure_brave()

    # Verify targets directory exists
    if not os.path.exists(config.TARGETS_DIR):
        print(f"[ERROR] Target images folder not found at: {config.TARGETS_DIR}")
        print("Please create the 'targets' directory and add your template PNG images.")
        return

    bot = BombCryptoBot()

    try:
        while True:
            bot.run_cycle()
            # Sleep between cycles (scan for errors every config.ERROR_CHECK_INTERVAL_SECONDS)
            time.sleep(config.ERROR_CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[BOT] Bot manually stopped by user (Ctrl+C). Exiting...")
    except Exception as e:
        print(f"\n[ERROR] Unexpected exception occurred: {e}")


if __name__ == "__main__":
    main()
