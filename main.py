import time
import sys
import os

# Add local path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from modules.bot_logic import BombCryptoBot

def main():
    print("==================================================")
    print("           BOMB CRYPTO AUTOMATION BOT             ")
    print("==================================================")
    print("Press Ctrl+C in terminal or move mouse to screen corner to emergency exit.")
    print(f"Target Images Directory: {config.TARGETS_DIR}")
    print(f"Direct Landing Mode: {config.DIRECT_LANDING_MODE}")
    print(f"Direct URL: {config.DIRECT_TREASURE_URL}")
    print(f"Hero Work Interval: {config.HERO_WORK_INTERVAL_MINUTES} minutes")
    print("==================================================\n")

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
