from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from modules import ensure_mouseinfo_mocked
from modules.bot_logic import BombCryptoBot
from modules.browser import BrowserManager
from modules.diagnostics import SystemDiagnostic, run_setup_wizard
from modules.logger import logger, setup_logging
from modules.notifications import NotificationManager

ensure_mouseinfo_mocked()


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
        "--game-version",
        type=str,
        choices=["auto", "v13d", "v10l"],
        default="auto",
        help="Game version mode: 'auto', 'v13d', or 'v10l'",
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
        "--work-all",
        "--work-all-heroes",
        action="store_true",
        help="Send all heroes to work regardless of stamina",
    )
    parser.add_argument(
        "--min-stamina",
        type=float,
        default=config.HERO_MIN_STAMINA,
        help="Minimum stamina percentage to send hero to work (default: 60)",
    )
    parser.add_argument(
        "--hero-work-mode",
        type=str,
        choices=["stamina", "all"],
        default=config.HERO_WORK_MODE,
        help="Hero work mode ('stamina' or 'all')",
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

    # Apply CLI argument or auto-detected browser URL overrides to config
    if args.game_version and args.game_version.lower() in ("v13d", "v10l"):
        config.GAME_VERSION = args.game_version.lower()
        if "DIRECT_TREASURE_URL" not in os.environ:
            if config.GAME_VERSION == "v10l":
                config.DIRECT_TREASURE_URL = "https://game.bombcrypto.io/web/v10l/index.html"
            else:
                config.DIRECT_TREASURE_URL = (
                    "https://game.bombcrypto.io/web/v13d/index.html?landing=treasure"
                )
        if "DIRECT_LANDING_MODE" not in os.environ:
            config.DIRECT_LANDING_MODE = config.GAME_VERSION == "v13d"
    else:
        # Auto-detect game version and URL from active open browser tab
        BrowserManager.sync_game_version_from_browser(try_clipboard=False)

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

    if args.min_stamina > 0:
        config.HERO_MIN_STAMINA = args.min_stamina

    if args.work_all:
        config.WORK_ONLY_STAMINA = False
        config.HERO_WORK_MODE = "all"
    elif args.hero_work_mode:
        config.HERO_WORK_MODE = args.hero_work_mode.lower()
        config.WORK_ONLY_STAMINA = config.HERO_WORK_MODE != "all"

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
    logger.info(f"  • Game Version:     {config.GAME_VERSION.upper()}")
    logger.info(f"  • Target Browser:   {config.TARGET_BROWSER.capitalize()}")
    logger.info(f"  • Attached Process: {browser_info['name']} (PID: {browser_info['pid']})")
    logger.info(f"  • Executable Path:  {browser_info['exe']}")
    logger.info(f"  • Status:           {browser_info['status']}")
    logger.info("--------------------------------------------------")
    logger.info(" [CLI & SYSTEM CONFIGURATION]")
    logger.info(f"  • Direct Game URL:  {config.DIRECT_TREASURE_URL}")
    logger.info(f"  • Direct Landing:   {config.DIRECT_LANDING_MODE}")
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
    if config.WORK_ONLY_STAMINA:
        logger.info(f"  • Hero Selection:   STAMINA (Min {config.HERO_MIN_STAMINA:.0f}%)")
    else:
        logger.info("  • Hero Selection:   ALL (Work All)")

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
    running = True

    def handle_shutdown(signum, frame):
        nonlocal running
        if running:
            running = False
            sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT (Ctrl+C)"
            logger.info(f"[BOT] Shutdown signal received ({sig_name}). Exiting cleanly...")
            logger.info(f"[SUMMARY] Final Runtime Performance Stats: {bot.get_stats_summary()}")
            NotificationManager.send_notification(
                "Bomb Crypto Bot Stopped",
                f"Bot stopped ({sig_name}). {bot.get_stats_summary()}",
                level="warning",
                sync=True,
            )
            sys.exit(0)

    try:
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
    except (ValueError, AttributeError):
        pass

    consecutive_errors = 0
    max_consecutive_errors = 5

    try:
        while running:
            try:
                bot.run_cycle()
                consecutive_errors = 0
            except Exception as cycle_err:
                consecutive_errors += 1
                logger.error(
                    f"[BOT ERROR] Error in cycle #{bot.cycles_completed} (Attempt {consecutive_errors}/{max_consecutive_errors}): {cycle_err}",
                    exc_info=True,
                )
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(
                        f"[BOT FATAL] Exceeded maximum consecutive cycle errors ({max_consecutive_errors}). Triggering emergency browser refresh..."
                    )
                    NotificationManager.send_notification(
                        "Bomb Crypto Bot Cycle Failure Limit",
                        f"Consecutive cycle errors limit reached ({max_consecutive_errors}). Triggering recovery refresh.",
                        level="error",
                    )
                    bot.handle_stuck_recovery()
                    consecutive_errors = 0

            time.sleep(config.ERROR_CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        handle_shutdown(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"[ERROR] Unexpected main process crash: {e}", exc_info=True)
        NotificationManager.send_notification(
            "Bomb Crypto Bot Error Crash",
            f"Unexpected process crash: {e}",
            level="error",
            sync=True,
        )


if __name__ == "__main__":
    main()
