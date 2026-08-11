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
from modules.browser import BrowserManager
from modules.diagnostics import SystemDiagnostic, run_setup_wizard
from modules.logger import logger, setup_logging
from modules.notifications import NotificationManager


def parse_args():
    parser = argparse.ArgumentParser(
        description="Bomb Crypto Automation Bot - Multi-platform Vision-driven Decision Engine"
    )
    parser.add_argument(
        "--check",
        "--check-system",
        action="store_true",
        dest="check_system",
        help="Run comprehensive system diagnostic test and verify dependencies, display, browser, and target assets",
    )
    parser.add_argument(
        "--setup",
        "--wizard",
        action="store_true",
        dest="setup_wizard",
        help="Run interactive setup wizard to create/configure .env file",
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
        "--browser",
        type=str,
        default=config.TARGET_BROWSER,
        help="Target web browser to attach/launch (brave / chrome / firefox / edge / default / auto)",
    )
    parser.add_argument(
        "--browser-path",
        type=str,
        default=config.BROWSER_EXECUTABLE_PATH,
        help="Custom absolute path to browser binary executable",
    )
    parser.add_argument(
        "--monitor",
        type=int,
        default=config.SCREENSHOT_MONITOR_INDEX,
        help="Screenshot monitor index (1 for primary monitor, 0 for all combined)",
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
        "--discord-webhook",
        type=str,
        default="",
        help="Discord Webhook URL for bot notifications",
    )
    parser.add_argument(
        "--telegram-token",
        type=str,
        default="",
        help="Telegram Bot Token for notifications",
    )
    parser.add_argument(
        "--telegram-chat-id",
        type=str,
        default="",
        help="Telegram Chat ID for notifications",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug-level logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Bomb Crypto Bot v2.2.0",
        help="Show bot version number and exit",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)

    if args.check_system:
        SystemDiagnostic.run_diagnostics()
        sys.exit(0)

    if args.setup_wizard:
        run_setup_wizard()
        sys.exit(0)

    # Apply CLI argument overrides to config
    config.HERO_WORK_INTERVAL_MINUTES = args.interval
    config.DRY_RUN = args.dry_run
    config.DEFAULT_MATCH_THRESHOLD = args.threshold
    config.SCREENSHOT_MONITOR_INDEX = args.monitor
    if args.browser:
        config.TARGET_BROWSER = args.browser.lower()
    if args.browser_path:
        config.BROWSER_EXECUTABLE_PATH = args.browser_path
    if args.headless:
        config.AUTO_LAUNCH_BROWSER = False
        config.AUTO_LAUNCH_BRAVE = False
    if args.discord_webhook:
        config.DISCORD_WEBHOOK_URL = args.discord_webhook
    if args.telegram_token:
        config.TELEGRAM_BOT_TOKEN = args.telegram_token
    if args.telegram_chat_id:
        config.TELEGRAM_CHAT_ID = args.telegram_chat_id

    if args.only_refresh_on_error:
        config.ONLY_REFRESH_ON_ERROR = True
        config.ENABLE_HERO_WORK_ACTIONS = False

    if args.refresh_interval > 0:
        config.REFRESH_INTERVAL_MINUTES = args.refresh_interval
        if not any(arg.startswith("--interval") for arg in sys.argv):
            config.ENABLE_HERO_WORK_ACTIONS = False

    if args.skip_hero_work:
        config.ENABLE_HERO_WORK_ACTIONS = False

    browser_info = BrowserManager.get_attached_browser_info()

    logger.info("==================================================")
    logger.info("       BOMB CRYPTO AUTOMATION BOT v2.2.0          ")
    logger.info("==================================================")
    logger.info(" [PLATFORM INFO]")
    logger.info(f"  • Operating System: {sys.platform}")
    logger.info(f"  • Target Browser:   {config.TARGET_BROWSER.capitalize()}")
    logger.info(f"  • Attached Process: {browser_info['name']} (PID: {browser_info['pid']})")
    logger.info(f"  • Executable Path:  {browser_info['exe']}")
    logger.info(f"  • Status:           {browser_info['status']}")
    logger.info("--------------------------------------------------")
    logger.info(" [CLI & SYSTEM CONFIGURATION]")
    logger.info(f"  • Direct Game URL:  {config.DIRECT_TREASURE_URL}")
    if config.ONLY_REFRESH_ON_ERROR:
        logger.info("  • Mode:             Only Refresh On Error (Inner Bot Active)")
    elif config.REFRESH_INTERVAL_MINUTES > 0:
        logger.info(
            f"  • Mode:             Periodic Page Refresh every {config.REFRESH_INTERVAL_MINUTES:.1f} min (Inner Bot Active)"
        )
    else:
        logger.info(
            f"  • Hero Work:        {'ENABLED (' + str(config.HERO_WORK_INTERVAL_MINUTES) + ' min cycle)' if config.ENABLE_HERO_WORK_ACTIONS else 'DISABLED (Inner Bot Active)'}"
        )

    logger.info(f"  • Match Threshold: {config.DEFAULT_MATCH_THRESHOLD:.2f}")
    logger.info(f"  • Screenshot Monitor: Index {config.SCREENSHOT_MONITOR_INDEX}")
    logger.info(
        f"  • Dry-Run Mode:    {'ENABLED (Simulation Only)' if config.DRY_RUN else 'Disabled (Live Mouse Actions)'}"
    )
    logger.info(f"  • Auto-Launch:     {'Disabled' if args.headless else 'Enabled'}")
    logger.info(f"  • Targets Folder:  {config.TARGETS_DIR}")
    logger.info("==================================================")
    logger.info("Press Ctrl+C or move mouse to screen corner to exit.\n")

    NotificationManager.send_notification(
        "Bomb Crypto Bot Initialized",
        f"Bot started with browser={config.TARGET_BROWSER}, interval={config.HERO_WORK_INTERVAL_MINUTES}m, dry_run={config.DRY_RUN}.",
        level="info",
    )

    if config.AUTO_LAUNCH_BROWSER:
        BrowserManager.verify_and_ensure_browser()

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
        logger.info(f"[SUMMARY] Final Runtime Performance Stats: {bot.get_stats_summary()}")
        NotificationManager.send_notification(
            "Bomb Crypto Bot Stopped",
            f"Bot manually stopped. {bot.get_stats_summary()}",
            level="warning",
        )
    except Exception as e:
        logger.error(f"[ERROR] Unexpected exception occurred: {e}", exc_info=True)
        NotificationManager.send_notification(
            "Bomb Crypto Bot Error Crash", f"Unexpected exception: {e}", level="error"
        )


if __name__ == "__main__":
    main()
