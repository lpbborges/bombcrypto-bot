import time
from enum import Enum, auto

import config
from modules.actions import ActionEngine
from modules.logger import logger
from modules.notifications import NotificationManager
from modules.vision import VisionEngine


class BotState(Enum):
    INITIALIZING = auto()
    CHECKING_ERRORS = auto()
    LOGGING_IN = auto()
    SENDING_HEROES = auto()
    ENTERING_MAP = auto()
    MAP_CLEARED = auto()
    RESTING = auto()
    STUCK_RECOVERY = auto()


def format_duration(seconds):
    """Formats duration into mm:ss:zzz (e.g. 05:23:450) or hh:mm:ss:zzz."""
    if seconds <= 0:
        return "00:00:000"
    mins, secs = divmod(int(seconds), 60)
    millis = int((seconds - int(seconds)) * 1000)
    if mins >= 60:
        hours, mins = divmod(mins, 60)
        return f"{hours:02d}:{mins:02d}:{secs:02d}:{millis:03d}"
    return f"{mins:02d}:{secs:02d}:{millis:03d}"


class BombCryptoBot:
    def __init__(self):
        self.vision = VisionEngine()
        self.state = BotState.INITIALIZING
        self.last_hero_work_time = 0
        self.last_progress_time = time.time()
        self.last_idle_jitter_time = 0
        self.last_periodic_refresh_time = time.time()
        self.start_time = time.time()

        # Bot runtime statistics
        self.cycles_completed = 0
        self.hero_work_cycles_count = 0
        self.errors_cleared_count = 0
        self.maps_cleared_count = 0
        self.stuck_recoveries_count = 0

    def get_stats_summary(self) -> str:
        """Returns formatted string summarizing runtime performance metrics."""
        uptime = format_duration(time.time() - self.start_time)
        return (
            f"Uptime: {uptime} | Cycles: {self.cycles_completed} | "
            f"Hero Work Cycles: {self.hero_work_cycles_count} | "
            f"Maps Cleared: {self.maps_cleared_count} | "
            f"Errors Cleared: {self.errors_cleared_count} | "
            f"Stuck Recoveries: {self.stuck_recoveries_count}"
        )

    def set_state(self, new_state: BotState):
        """Transitions bot state with logging."""
        if self.state != new_state:
            logger.info(f"[BOT FSM] Transitioning state: {self.state.name} -> {new_state.name}")
            self.state = new_state

    def check_idle_jitter(self):
        """
        Executes anti-AFK idle jitter if bot is in RESTING state and interval has elapsed.
        """
        if getattr(config, "ENABLE_IDLE_JITTER", True) and self.state == BotState.RESTING:
            jitter_interval = getattr(config, "IDLE_JITTER_INTERVAL_SECONDS", 30)
            if time.time() - self.last_idle_jitter_time >= jitter_interval:
                ActionEngine.idle_jitter()
                self.last_idle_jitter_time = time.time()

    def update_progress(self):
        """Resets the anti-stuck timeout timer upon successful action/progression."""
        self.last_progress_time = time.time()

    def check_stuck_timeout(self) -> bool:
        """
        Checks if the bot has been stuck in the same unprogressive state beyond config.MAX_STUCK_TIMEOUT_MINUTES.
        Triggers STUCK_RECOVERY state if timeout exceeded.
        """
        if self.state == BotState.STUCK_RECOVERY:
            return True

        stuck_duration = time.time() - self.last_progress_time
        max_stuck_seconds = config.MAX_STUCK_TIMEOUT_MINUTES * 60.0

        if stuck_duration >= max_stuck_seconds:
            stuck_mins = stuck_duration / 60.0
            msg = (
                f"No progress detected for {stuck_mins:.1f} minutes "
                f"(exceeds threshold of {config.MAX_STUCK_TIMEOUT_MINUTES} min). Triggering anti-stuck recovery..."
            )
            logger.warning(f"[BOT STUCK ALERT] {msg}")
            self.stuck_recoveries_count += 1
            NotificationManager.notify_stuck_recovery(msg)
            self.set_state(BotState.STUCK_RECOVERY)
            return True

        return False

    def handle_stuck_recovery(self):
        """Executes browser page refresh to recover from frozen/stuck state."""
        logger.info("[BOT RECOVERY] Refreshing browser page to recover from stuck state...")
        ActionEngine.refresh_page()
        self.vision.clear_cache()
        self.update_progress()
        self.last_periodic_refresh_time = time.time()
        self.set_state(BotState.INITIALIZING)

    def check_periodic_refresh(self) -> bool:
        """
        Checks if the configured periodic page refresh interval has elapsed.
        Refreshes browser page to prevent/recover stuck heroes when inner bot is active.
        """
        interval_mins = getattr(config, "REFRESH_INTERVAL_MINUTES", 0.0)
        if interval_mins <= 0:
            return False

        elapsed_seconds = time.time() - self.last_periodic_refresh_time
        interval_seconds = interval_mins * 60.0

        if elapsed_seconds >= interval_seconds:
            elapsed_str = format_duration(elapsed_seconds)
            logger.info(
                f"[BOT REFRESH] Periodic refresh interval reached ({elapsed_str} elapsed / {interval_mins:.1f} min threshold). "
                f"Refreshing browser page to unstuck heroes..."
            )
            NotificationManager.send_notification(
                "Bomb Crypto Bot Periodic Refresh",
                f"Refreshing page after {interval_mins:.1f}m interval to unstuck heroes.",
                level="info",
            )
            ActionEngine.refresh_page()
            self.vision.clear_cache()
            self.update_progress()
            self.last_periodic_refresh_time = time.time()
            self.set_state(BotState.INITIALIZING)
            return True

        return False

    def check_errors_or_disconnect(self) -> bool:
        """
        Scans for common game error modals (error_message/unknown_error)
        or error OK buttons (error_ok_button/error_ok).
        Returns True if an error was handled or page refreshed.
        """
        logger.info("[BOT] Scanning for error popups or disconnects...")
        screen = self.vision.capture_screen()

        # Check for 'OK' error button (checking error_ok_button first, then error_ok)
        ok_match = self.vision.find_template(
            config.TARGET_IMAGES["error_ok_button"], screen_gray=screen
        ) or self.vision.find_template(config.TARGET_IMAGES["error_ok"], screen_gray=screen)

        if ok_match:
            logger.info(
                f"[BOT] Error popup OK button detected (Confidence: {ok_match['confidence']:.2f}). Clicking OK..."
            )
            self.errors_cleared_count += 1
            NotificationManager.notify_error_cleared("Error OK Button")
            ActionEngine.click_match(ok_match)
            self.vision.clear_cache()
            self.update_progress()
            return True

        # Check for error message modal (error_message or unknown_error)
        err_msg_match = self.vision.find_template(
            config.TARGET_IMAGES["error_message"], screen_gray=screen
        ) or self.vision.find_template(config.TARGET_IMAGES["unknown_error"], screen_gray=screen)

        if err_msg_match:
            logger.info(
                f"[BOT] Error message modal detected (Confidence: {err_msg_match['confidence']:.2f})."
            )
            self.errors_cleared_count += 1
            # Try to see if an OK button is present to dismiss the error message modal
            ok_match = self.vision.find_template(
                config.TARGET_IMAGES["error_ok_button"], screen_gray=screen
            ) or self.vision.find_template(config.TARGET_IMAGES["error_ok"], screen_gray=screen)

            if ok_match:
                logger.info("[BOT] Found OK button for error message. Clicking OK...")
                NotificationManager.notify_error_cleared("Error Message OK Button")
                ActionEngine.click_match(ok_match)
            else:
                logger.info("[BOT] No OK button found for error message modal. Refreshing page...")
                NotificationManager.notify_error_cleared("Error Message Modal")
                ActionEngine.refresh_page()
                self.last_periodic_refresh_time = time.time()

            self.vision.clear_cache()
            self.update_progress()
            return True

        return False

    def handle_login(self) -> bool:
        """
        Flexibly handles login/reconnect states without duplicate click spam.
        """
        screen = self.vision.capture_screen()

        # Step 1: Check for profile confirmation 'OK' button first
        profile_ok = self.vision.find_template(
            config.TARGET_IMAGES["confirm_profile_ok"], screen_gray=screen
        )
        if profile_ok:
            logger.info(
                f"[BOT] Confirm profile button ('OK') found (Confidence: {profile_ok['confidence']:.2f}). Clicking OK..."
            )
            ActionEngine.click_match(profile_ok)
            self.vision.clear_cache()
            ActionEngine.human_delay(4.0, 6.0)
            self.update_progress()
            return True

        # Step 2: Check for MetaMask Sign/Confirm button popup standalone
        metamask_sign = self.vision.find_template(
            config.TARGET_IMAGES["metamask_sign"], screen_gray=screen
        )
        if metamask_sign:
            logger.info(
                f"[BOT] MetaMask Sign/Confirm button found (Confidence: {metamask_sign['confidence']:.2f}). Signing transaction..."
            )
            ActionEngine.click_match(metamask_sign)
            self.vision.clear_cache()
            ActionEngine.human_delay(5.0, 8.0)
            self.update_progress()
            return True

        # Step 3: Check for Select MetaMask modal standalone
        wallet_select = self.vision.find_template(
            config.TARGET_IMAGES["select_metamask"], screen_gray=screen
        )
        if wallet_select:
            logger.info(
                f"[BOT] Select MetaMask icon found (Confidence: {wallet_select['confidence']:.2f}). Clicking..."
            )
            ActionEngine.click_match(wallet_select)
            self.vision.clear_cache()
            ActionEngine.human_delay(3.0, 5.0)
            self.update_progress()
            return True

        # Step 4: Check for 'Connect Wallet' button
        connect_match = self.vision.find_template(
            config.TARGET_IMAGES["connect_wallet"], screen_gray=screen
        )
        if connect_match:
            logger.info(
                f"[BOT] 'Connect Wallet' button found (Confidence: {connect_match['confidence']:.2f}). Initiating login..."
            )
            ActionEngine.click_match(connect_match)
            self.vision.clear_cache()
            ActionEngine.human_delay(4.0, 6.0)
            self.update_progress()

            # Check if wallet selection modal pops up immediately after
            screen_after = self.vision.capture_screen(force_refresh=True)
            wallet_select = self.vision.find_template(
                config.TARGET_IMAGES["select_metamask"], screen_gray=screen_after
            )
            if wallet_select:
                logger.info(
                    f"[BOT] Select MetaMask icon found (Confidence: {wallet_select['confidence']:.2f}). Clicking..."
                )
                ActionEngine.click_match(wallet_select)
                self.vision.clear_cache()
                ActionEngine.human_delay(3.0, 5.0)

            # Check for MetaMask Sign button popup
            metamask_sign = self.vision.find_template(
                config.TARGET_IMAGES["metamask_sign"], screen_gray=screen_after
            )
            if metamask_sign:
                logger.info(
                    f"[BOT] MetaMask Sign button found (Confidence: {metamask_sign['confidence']:.2f}). Signing transaction..."
                )
                ActionEngine.click_match(metamask_sign)
                self.vision.clear_cache()
                ActionEngine.human_delay(5.0, 8.0)

            return True

        return False

    def send_heroes_to_work(self) -> bool:
        """
        Sequence:
        1. Click the bottom arrow to expand the bottom menu.
        2. Click 'heroes_button' inside the opened menu.
        3. Click 'Work All' inside the heroes modal.
        4. Click close modal button ('X').
        """
        logger.info("[BOT] Attempting to send heroes to work...")
        screen = self.vision.capture_screen()

        # Step 1: Find & click bottom arrow to open menu
        bottom_arrow_match = self.vision.find_template(
            config.TARGET_IMAGES["bottom_arrow"], screen_gray=screen
        )
        if bottom_arrow_match:
            logger.info(
                f"[BOT] Found bottom arrow menu button (Confidence: {bottom_arrow_match['confidence']:.2f}). Opening menu..."
            )
            ActionEngine.click_match(bottom_arrow_match)
            self.vision.clear_cache()
            ActionEngine.human_delay(2.0, 4.0)
            screen = self.vision.capture_screen(force_refresh=True)
        else:
            logger.info(
                "[BOT] Bottom arrow menu button not found directly; checking if menu is already open..."
            )

        # Step 2: Click Heroes Button inside opened menu
        heroes_match = self.vision.find_template(
            config.TARGET_IMAGES["heroes_button"], screen_gray=screen
        )
        if heroes_match:
            logger.info(
                f"[BOT] Found Heroes button inside menu (Confidence: {heroes_match['confidence']:.2f}). Opening heroes list..."
            )
            ActionEngine.click_match(heroes_match)
            self.vision.clear_cache()
            ActionEngine.human_delay(2.5, 4.5)

            # Step 3: Check hero action buttons inside heroes modal
            work_all_screen = self.vision.capture_screen(force_refresh=True)
            rest_all_match = self.vision.find_template(
                config.TARGET_IMAGES["rest_all_button"], screen_gray=work_all_screen
            )
            if rest_all_match:
                logger.info(
                    f"[BOT] 'Rest All' button detected (Confidence: {rest_all_match['confidence']:.2f}). All heroes are already working, taking no action."
                )
            else:
                work_all_match = self.vision.find_template(
                    config.TARGET_IMAGES["work_all_button"], screen_gray=work_all_screen
                )
                if work_all_match:
                    logger.info(
                        f"[BOT] Clicking 'Work All' button (Confidence: {work_all_match['confidence']:.2f})..."
                    )
                    ActionEngine.click_match(work_all_match)
                    self.vision.clear_cache()
                    ActionEngine.human_delay(2.0, 3.5)
                else:
                    logger.warning("[BOT] Neither 'Work All' nor 'Rest All' button image found.")

            # Step 4: Close Heroes Modal
            close_screen = self.vision.capture_screen(force_refresh=True)
            close_match = self.vision.find_template(
                config.TARGET_IMAGES["close_button"], screen_gray=close_screen
            )
            if close_match:
                logger.info(
                    f"[BOT] Closing Heroes menu (Confidence: {close_match['confidence']:.2f})..."
                )
                ActionEngine.click_match(close_match)
                self.vision.clear_cache()
                ActionEngine.human_delay(1.5, 2.5)

            # Step 5: Click screen center to collapse HUD menu
            center_x = screen.shape[1] // 2
            center_y = screen.shape[0] // 2
            logger.info(
                f"[BOT] Clicking screen center ({center_x}, {center_y}) to collapse HUD menu..."
            )
            ActionEngine.click_at(center_x, center_y)
            self.vision.clear_cache()
            ActionEngine.human_delay(1.5, 2.5)

            self.last_hero_work_time = time.time()
            self.hero_work_cycles_count += 1
            self.update_progress()
            NotificationManager.notify_hero_cycle("Heroes sent to work successfully.")
            return True

        logger.info("[BOT] Heroes button not visible on screen.")
        return False

    def enter_treasure_hunt(self) -> bool:
        """
        Ensures game is in Treasure Hunt mode.
        If DIRECT_LANDING_MODE is enabled, the direct URL lands straight into Treasure Hunt.
        Otherwise, attempts to locate and click the Treasure Hunt icon.
        """
        if config.DIRECT_LANDING_MODE:
            logger.info(
                "[BOT] Direct Treasure Hunt landing mode enabled. Skipping main menu icon click."
            )
            self.update_progress()
            return True

        screen = self.vision.capture_screen()
        th_match = self.vision.find_template(
            config.TARGET_IMAGES["treasure_hunt_icon"], screen_gray=screen
        )
        if th_match:
            logger.info(
                f"[BOT] Found Treasure Hunt map icon (Confidence: {th_match['confidence']:.2f}). Entering map..."
            )
            ActionEngine.click_match(th_match)
            self.vision.clear_cache()
            ActionEngine.human_delay(2.0, 4.0)
            self.update_progress()
            return True

        return False

    def check_map_cleared(self) -> bool:
        """
        Scans for 'Map Cleared' banner or completion button.
        Clicks button or banner to transition to next map.
        """
        logger.info("[BOT] Scanning for Map Cleared indicators...")
        screen = self.vision.capture_screen()

        # Step 1: Check for map_complete_button first
        button_match = self.vision.find_template(
            config.TARGET_IMAGES["map_complete_button"], screen_gray=screen
        )
        if button_match:
            logger.info(
                f"[BOT] 'Map Cleared' button detected (Confidence: {button_match['confidence']:.2f}). Transitioning map..."
            )
            self.maps_cleared_count += 1
            NotificationManager.notify_map_cleared()
            self.set_state(BotState.MAP_CLEARED)
            ActionEngine.click_match(button_match)
            self.vision.clear_cache()
            ActionEngine.human_delay(3.0, 5.0)
            self.update_progress()
            self.set_state(BotState.RESTING)
            return True

        # Step 2: Check for map_complete modal as fallback
        map_match = self.vision.find_template(
            config.TARGET_IMAGES["map_complete"], screen_gray=screen
        )
        if map_match:
            logger.info(
                f"[BOT] 'Map Cleared' modal detected (Confidence: {map_match['confidence']:.2f}). Transitioning map..."
            )
            self.maps_cleared_count += 1
            NotificationManager.notify_map_cleared()
            self.set_state(BotState.MAP_CLEARED)
            ActionEngine.click_match(map_match)
            self.vision.clear_cache()
            ActionEngine.human_delay(3.0, 5.0)
            self.update_progress()
            self.set_state(BotState.RESTING)
            return True

        return False

    def run_cycle(self):
        """
        FSM-driven main decision cycle for the bot.
        """
        self.cycles_completed += 1
        logger.info(
            f"--- [BOT CYCLE #{self.cycles_completed} START - State: {self.state.name}] ---"
        )
        logger.debug(f"[METRICS] {self.get_stats_summary()}")

        # Invalidate frame cache at start of cycle
        self.vision.clear_cache()

        # Step 1: Check anti-stuck timeout recovery
        if self.check_stuck_timeout():
            self.handle_stuck_recovery()
            logger.info("--- [BOT CYCLE END] ---")
            return

        # Step 2: Handle STUCK_RECOVERY state directly if set
        if self.state == BotState.STUCK_RECOVERY:
            self.handle_stuck_recovery()
            logger.info("--- [BOT CYCLE END] ---")
            return

        # Step 3: Global Error & Disconnect scan
        if self.check_errors_or_disconnect():
            self.set_state(BotState.CHECKING_ERRORS)
            logger.info("--- [BOT CYCLE END] ---")
            return

        # Step 4: Check Login requirement
        if self.handle_login():
            self.set_state(BotState.LOGGING_IN)
            logger.info("--- [BOT CYCLE END] ---")
            return

        # Step 5: Check Periodic Refresh requirement (Inner Bot periodic unstuck)
        if self.check_periodic_refresh():
            logger.info("--- [BOT CYCLE END] ---")
            return

        # Step 6: Check Map Cleared requirement
        if self.check_map_cleared():
            logger.info("--- [BOT CYCLE END] ---")
            return

        # Step 7: FSM Work & Resting Cycle Logic
        only_error_refresh = getattr(config, "ONLY_REFRESH_ON_ERROR", False)
        hero_work_enabled = getattr(config, "ENABLE_HERO_WORK_ACTIONS", True)

        if only_error_refresh or not hero_work_enabled:
            mode_desc = "Error-Only Refresh" if only_error_refresh else "Inner Bot Monitoring"
            logger.info(
                f"[BOT] State: {self.state.name} | Inner Bot active ({mode_desc}). "
                f"Monitoring for errors or stuck state..."
            )
            if self.state != BotState.RESTING and self.enter_treasure_hunt():
                self.set_state(BotState.RESTING)

            self.check_idle_jitter()
        else:
            if self.last_hero_work_time == 0:
                logger.info("[BOT] Initial work cycle starting. Transitioning to SENDING_HEROES...")
                self.set_state(BotState.SENDING_HEROES)
                if self.send_heroes_to_work():
                    self.set_state(BotState.ENTERING_MAP)
                    self.enter_treasure_hunt()
                    self.set_state(BotState.RESTING)
            else:
                elapsed_seconds = time.time() - self.last_hero_work_time
                interval_seconds = config.HERO_WORK_INTERVAL_MINUTES * 60.0

                if elapsed_seconds >= interval_seconds:
                    elapsed_str = format_duration(elapsed_seconds)
                    logger.info(
                        f"[BOT] Work interval reached ({elapsed_str} elapsed). Transitioning to SENDING_HEROES..."
                    )
                    self.set_state(BotState.SENDING_HEROES)
                    if self.send_heroes_to_work():
                        self.set_state(BotState.ENTERING_MAP)
                        self.enter_treasure_hunt()
                        self.set_state(BotState.RESTING)
                else:
                    remaining_seconds = interval_seconds - elapsed_seconds
                    elapsed_str = format_duration(elapsed_seconds)
                    remaining_str = format_duration(remaining_seconds)
                    logger.info(
                        f"[BOT] State: {self.state.name} | Heroes working/resting ({elapsed_str} elapsed). "
                        f"Next work cycle in {remaining_str}."
                    )

                    # Ensure we are inside Treasure Hunt map
                    if self.state != BotState.RESTING and self.enter_treasure_hunt():
                        self.set_state(BotState.RESTING)

                    # Execute anti-AFK idle jitter if resting
                    self.check_idle_jitter()

        logger.info("--- [BOT CYCLE END] ---")
