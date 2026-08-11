import argparse
import logging
import os
import sys
import time
import types

if "mouseinfo" not in sys.modules:
    dummy_mouseinfo = types.ModuleType("mouseinfo")
    dummy_mouseinfo.MouseInfoWindow = lambda *a, **k: None
    sys.modules["mouseinfo"] = dummy_mouseinfo

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from modules.bot_logic import BombCryptoBot
from modules.browser import BraveManager
from modules.logger import logger, setup_logging
from modules.notifications import NotificationManager


def parse_args():
    parser = argparse.ArgumentParser(
        description="Bomb Crypto Automation Bot - Anti-detection & Vision-driven decision engine"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=config.HERO_WORK_INTERVAL_MINUTES,
        help="Hero work cycle interval in minutes (default: 30)",
    )
    parser.add_argument(
        "--only-refresh-on-error",
        action="store_true",
        help="Inner Bot Mode: Only refresh the page when an error or disconnect popup is detected",
    )
    parser.add_argument(
        "--refresh-interval",
        type=float,
        default=config.REFRESH_INTERVAL_MINUTES,
        help="Inner Bot Mode: Periodic page refresh interval in minutes to unstuck heroes (0 to disable)",
    )
    parser.add_argument(
        "--skip-hero-work",
        action="store_true",
        help="Skip manual hero work clicking sequence (useful when game inner bot is active)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: simulates actions and vision matching without physical mouse clicking",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=config.DEFAULT_MATCH_THRESHOLD,
        help="Override global template matching confidence threshold (0.0 - 1.0)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Disable browser auto-launch (assumes browser is managed externally)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug-level logging",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)

    config.HERO_WORK_INTERVAL_MINUTES = args.interval
    config.DRY_RUN = args.dry_run
    config.DEFAULT_MATCH_THRESHOLD = args.threshold
    if args.headless:
        config.AUTO_LAUNCH_BRAVE = False

    if args.only_refresh_on_error:
        config.ONLY_REFRESH_ON_ERROR = True
        config.ENABLE_HERO_WORK_ACTIONS = False

    if args.refresh_interval > 0:
        config.REFRESH_INTERVAL_MINUTES = args.refresh_interval
        if not any(arg.startswith("--interval") for arg in sys.argv):
            config.ENABLE_HERO_WORK_ACTIONS = False

    if args.skip_hero_work:
        config.ENABLE_HERO_WORK_ACTIONS = False

    browser_info = BraveManager.get_attached_browser_info()

    logger.info("==================================================")
    logger.info("           BOMB CRYPTO AUTOMATION BOT             ")
    logger.info("==================================================")
    logger.info(" [ATTACHED BROWSER INFO]")
    logger.info(f"  • Name:       {browser_info['name']}")
    logger.info(f"  • Process ID: PID {browser_info['pid']}")
    logger.info(f"  • Binary Exe: {browser_info['exe']}")
    logger.info(f"  • Status:     {browser_info['status']}")
    logger.info("--------------------------------------------------")
    logger.info(" [CLI CONFIGURATION]")
    logger.info(f"  • Direct URL: {config.DIRECT_TREASURE_URL}")
    if config.ONLY_REFRESH_ON_ERROR:
        logger.info("  • Mode:       Only Refresh On Error (Inner Bot Active)")
    elif config.REFRESH_INTERVAL_MINUTES > 0:
        logger.info(f"  • Mode:       Periodic Page Refresh every {config.REFRESH_INTERVAL_MINUTES:.1f} min (Inner Bot Active)")
    else:
        logger.info(f"  • Hero Work:  {'ENABLED (' + str(config.HERO_WORK_INTERVAL_MINUTES) + ' min cycle)' if config.ENABLE_HERO_WORK_ACTIONS else 'DISABLED (Inner Bot Active)'}")

    logger.info(f"  • Threshold:  {config.DEFAULT_MATCH_THRESHOLD:.2f} default match threshold")
    logger.info(
        f"  • Dry-Run:    {'ENABLED (Simulation)' if config.DRY_RUN else 'Disabled (Live Actions)'}"
    )
    logger.info(
        f"  • Headless:   {'Disabled Auto-Launch' if args.headless else 'Auto-Launch Enabled'}"
    )
    logger.info(f"  • Targets:    {config.TARGETS_DIR}")
    logger.info("==================================================")
    logger.info("Press Ctrl+C or move mouse to screen corner to exit.\n")


    NotificationManager.send_notification(
        "Bomb Crypto Bot Initialized",
        f"Bot started with interval={config.HERO_WORK_INTERVAL_MINUTES}m, dry_run={config.DRY_RUN}.",
        level="info",
    )

    if config.AUTO_LAUNCH_BRAVE:
        BraveManager.verify_and_ensure_brave()

    if not os.path.exists(config.TARGETS_DIR):
        logger.error(f"Target images folder not found at: {config.TARGETS_DIR}")
        logger.error("Please create the 'targets' directory and add your template PNG images.")
        return

    bot = BombCryptoBot()

    try:
        while True:
            bot.run_cycle()
            time.sleep(config.ERROR_CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("[BOT] Bot manually stopped by user (Ctrl+C). Exiting...")
        NotificationManager.send_notification(
            "Bomb Crypto Bot Stopped", "Bot manually stopped by user (Ctrl+C).", level="warning"
        )
    except Exception as e:
        logger.error(f"[ERROR] Unexpected exception occurred: {e}", exc_info=True)
        NotificationManager.send_notification(
            "Bomb Crypto Bot Error Crash", f"Unexpected exception: {e}", level="error"
        )


if __name__ == "__main__":
    main()
