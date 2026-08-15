from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BotConfig
from modules import ensure_mouseinfo_mocked
from modules.bot_logic import BombCryptoBot
from modules.browser import BrowserManager
from modules.diagnostics import SystemDiagnostic, run_setup_wizard
from modules.logger import logger, setup_logging
from modules.notifications import NotificationManager

ensure_mouseinfo_mocked()


def parse_args():
    cfg_defaults = BotConfig()
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
        default="auto",
        help="Game version mode: 'auto', 'v13', or 'v10'",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=cfg_defaults.hero_work_interval_minutes,
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
        default=cfg_defaults.refresh_interval_minutes,
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
        default=cfg_defaults.hero_min_stamina,
        help="Minimum stamina percentage to send hero to work (default: 60)",
    )
    parser.add_argument(
        "--hero-work-mode",
        type=str,
        choices=["stamina", "all"],
        default=cfg_defaults.hero_work_mode,
        help="Hero work mode ('stamina' or 'all')",
    )
    parser.add_argument(
        "--browser",
        type=str,
        default=cfg_defaults.target_browser,
        help="Target web browser to attach/launch (brave / chrome / firefox / edge / default / auto)",
    )
    parser.add_argument(
        "--browser-path",
        type=str,
        default=cfg_defaults.browser_executable_path,
        help="Custom absolute path to browser binary executable",
    )
    parser.add_argument(
        "--monitor",
        type=int,
        default=cfg_defaults.screenshot_monitor_index,
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
        default=cfg_defaults.default_match_threshold,
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

    cfg = BotConfig()

    if args.check_system:
        SystemDiagnostic.config = cfg
        SystemDiagnostic.run_diagnostics()
        sys.exit(0)

    if args.setup_wizard:
        run_setup_wizard()
        sys.exit(0)

    # Apply CLI argument or auto-detected browser URL overrides to config
    if args.game_version and args.game_version.lower() not in ("auto", ""):
        gv = args.game_version.lower()
        if gv.startswith("v10"):
            cfg.game_version = "v10"
        else:
            cfg.game_version = "v13"
        if "DIRECT_TREASURE_URL" not in os.environ:
            if cfg.game_version == "v10":
                cfg.direct_treasure_url = "https://game.bombcrypto.io/web/v10/index.html"
            else:
                cfg.direct_treasure_url = (
                    "https://game.bombcrypto.io/web/v13e/index.html?landing=treasure"
                )
        if "DIRECT_LANDING_MODE" not in os.environ:
            cfg.direct_landing_mode = cfg.game_version == "v13"
    else:
        # Auto-detect game version and URL from active open browser tab
        BrowserManager.config = cfg
        BrowserManager.sync_game_version_from_browser(try_clipboard=False)

    cfg.hero_work_interval_minutes = args.interval
    cfg.dry_run = args.dry_run
    cfg.default_match_threshold = args.threshold
    cfg.screenshot_monitor_index = args.monitor
    if args.browser:
        cfg.target_browser = args.browser.lower()
    if args.browser_path:
        cfg.browser_executable_path = args.browser_path
    if args.headless:
        cfg.auto_launch_browser = False
        cfg.auto_launch_brave = False
    if args.discord_webhook:
        cfg.discord_webhook_url = args.discord_webhook
    if args.telegram_token:
        cfg.telegram_bot_token = args.telegram_token
    if args.telegram_chat_id:
        cfg.telegram_chat_id = args.telegram_chat_id

    if args.min_stamina > 0:
        cfg.hero_min_stamina = args.min_stamina

    if args.work_all:
        cfg.work_only_stamina = False
        cfg.hero_work_mode = "all"
    elif args.hero_work_mode:
        cfg.hero_work_mode = args.hero_work_mode.lower()
        cfg.work_only_stamina = cfg.hero_work_mode != "all"

    if args.only_refresh_on_error:
        cfg.only_refresh_on_error = True
        cfg.enable_hero_work_actions = False

    if args.refresh_interval > 0:
        cfg.refresh_interval_minutes = args.refresh_interval
        if not any(arg.startswith("--interval") for arg in sys.argv):
            cfg.enable_hero_work_actions = False

    if args.skip_hero_work:
        cfg.enable_hero_work_actions = False

    BrowserManager.config = cfg
    SystemDiagnostic.config = cfg
    NotificationManager.config = cfg

    browser_info = BrowserManager.get_attached_browser_info()

    logger.info("==================================================")
    logger.info("       BOMB CRYPTO AUTOMATION BOT v2.2.0          ")
    logger.info("==================================================")
    logger.info(" [PLATFORM INFO]")
    logger.info(f"  • Operating System: {sys.platform}")
    logger.info(f"  • Game Version:     {cfg.game_version.upper()}")
    logger.info(f"  • Target Browser:   {cfg.target_browser.capitalize()}")
    logger.info(f"  • Attached Process: {browser_info['name']} (PID: {browser_info['pid']})")
    logger.info(f"  • Executable Path:  {browser_info['exe']}")
    logger.info(f"  • Status:           {browser_info['status']}")
    logger.info("--------------------------------------------------")
    logger.info(" [CLI & SYSTEM CONFIGURATION]")
    logger.info(f"  • Direct Game URL:  {cfg.direct_treasure_url}")
    logger.info(f"  • Direct Landing:   {cfg.direct_landing_mode}")
    if cfg.only_refresh_on_error:
        logger.info("  • Mode:             Only Refresh On Error (Inner Bot Active)")
    elif cfg.refresh_interval_minutes > 0:
        logger.info(
            f"  • Mode:             Periodic Page Refresh every {cfg.refresh_interval_minutes:.1f} min (Inner Bot Active)"
        )
    else:
        logger.info(
            f"  • Hero Work:        {'ENABLED (' + str(cfg.hero_work_interval_minutes) + ' min cycle)' if cfg.enable_hero_work_actions else 'DISABLED (Inner Bot Active)'}"
        )
    if cfg.work_only_stamina:
        logger.info(f"  • Hero Selection:   STAMINA (Min {cfg.hero_min_stamina:.0f}%)")
    else:
        logger.info("  • Hero Selection:   ALL (Work All)")

    logger.info(f"  • Match Threshold: {cfg.default_match_threshold:.2f}")
    logger.info(f"  • Screenshot Monitor: Index {cfg.screenshot_monitor_index}")
    logger.info(
        f"  • Dry-Run Mode:    {'ENABLED (Simulation Only)' if cfg.dry_run else 'Disabled (Live Mouse Actions)'}"
    )
    logger.info(f"  • Auto-Launch:     {'Disabled' if args.headless else 'Enabled'}")
    logger.info(f"  • Targets Folder:  {cfg.targets_dir}")
    logger.info("==================================================")
    logger.info("Press Ctrl+C or move mouse to screen corner to exit.\n")

    NotificationManager.send_notification(
        "Bomb Crypto Bot Initialized",
        f"Bot started with browser={cfg.target_browser}, interval={cfg.hero_work_interval_minutes}m, dry_run={cfg.dry_run}.",
        level="info",
    )

    if cfg.auto_launch_browser:
        BrowserManager.verify_and_ensure_browser()

    if not os.path.exists(cfg.targets_dir):
        logger.error(f"Target images folder not found at: {cfg.targets_dir}")
        logger.error("Please create the 'targets' directory and add your template PNG images.")
        return

    bot = BombCryptoBot(cfg)
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

            time.sleep(cfg.error_check_interval_seconds)
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
