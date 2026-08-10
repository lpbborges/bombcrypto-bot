import time
from enum import Enum, auto

import config
from modules.actions import ActionEngine
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

    def set_state(self, new_state: BotState):
        """Transitions bot state with logging."""
        if self.state != new_state:
            print(f"[BOT FSM] Transitioning state: {self.state.name} -> {new_state.name}")
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
            print(
                f"\n[BOT STUCK ALERT] No progress detected for {stuck_mins:.1f} minutes "
                f"(exceeds threshold of {config.MAX_STUCK_TIMEOUT_MINUTES} min). Triggering anti-stuck recovery..."
            )
            self.set_state(BotState.STUCK_RECOVERY)
            return True

        return False

    def handle_stuck_recovery(self):
        """Executes browser page refresh to recover from frozen/stuck state."""
        print("[BOT RECOVERY] Refreshing browser page to recover from stuck state...")
        ActionEngine.refresh_page()
        self.vision.clear_cache()
        self.update_progress()
        self.set_state(BotState.INITIALIZING)

    def check_errors_or_disconnect(self) -> bool:
        """
        Scans for common game error modals or disconnect OK buttons.
        Returns True if an error was handled or page refreshed.
        """
        print("[BOT] Scanning for error popups or disconnects...")
        screen = self.vision.capture_screen()

        # Check for 'OK' error button
        ok_match = self.vision.find_template(config.TARGET_IMAGES["error_ok"], screen_gray=screen)
        if ok_match:
            print(
                f"[BOT] Error popup detected (Confidence: {ok_match['confidence']:.2f}). Clicking OK..."
            )
            ActionEngine.click_match(ok_match)
            self.vision.clear_cache()
            self.update_progress()
            return True

        # Check for 'Unknown Error' modal
        unk_match = self.vision.find_template(
            config.TARGET_IMAGES["unknown_error"], screen_gray=screen
        )
        if unk_match:
            print(
                f"[BOT] Unknown error detected (Confidence: {unk_match['confidence']:.2f}). Refreshing page..."
            )
            ActionEngine.refresh_page()
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
            print(
                f"[BOT] Confirm profile button ('OK') found (Confidence: {profile_ok['confidence']:.2f}). Clicking OK..."
            )
            ActionEngine.click_match(profile_ok)
            self.vision.clear_cache()
            ActionEngine.human_delay(4.0, 6.0)
            self.update_progress()
            return True

        # Step 2: Check for 'Connect Wallet' button
        connect_match = self.vision.find_template(
            config.TARGET_IMAGES["connect_wallet"], screen_gray=screen
        )
        if connect_match:
            print(
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
                print(
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
                print(
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
        print("[BOT] Attempting to send heroes to work...")
        screen = self.vision.capture_screen()

        # Step 1: Find & click bottom arrow to open menu
        bottom_arrow_match = self.vision.find_template(
            config.TARGET_IMAGES["bottom_arrow"], screen_gray=screen
        )
        if bottom_arrow_match:
            print(
                f"[BOT] Found bottom arrow menu button (Confidence: {bottom_arrow_match['confidence']:.2f}). Opening menu..."
            )
            ActionEngine.click_match(bottom_arrow_match)
            self.vision.clear_cache()
            ActionEngine.human_delay(2.0, 4.0)
            screen = self.vision.capture_screen(force_refresh=True)
        else:
            print(
                "[BOT] Bottom arrow menu button not found directly; checking if menu is already open..."
            )

        # Step 2: Click Heroes Button inside opened menu
        heroes_match = self.vision.find_template(
            config.TARGET_IMAGES["heroes_button"], screen_gray=screen
        )
        if heroes_match:
            print(
                f"[BOT] Found Heroes button inside menu (Confidence: {heroes_match['confidence']:.2f}). Opening heroes list..."
            )
            ActionEngine.click_match(heroes_match)
            self.vision.clear_cache()
            ActionEngine.human_delay(2.5, 4.5)

            # Step 3: Click 'Work All' button inside heroes modal
            work_all_screen = self.vision.capture_screen(force_refresh=True)
            work_all_match = self.vision.find_template(
                config.TARGET_IMAGES["work_all_button"], screen_gray=work_all_screen
            )
            if work_all_match:
                print(
                    f"[BOT] Clicking 'Work All' button (Confidence: {work_all_match['confidence']:.2f})..."
                )
                ActionEngine.click_match(work_all_match)
                self.vision.clear_cache()
                ActionEngine.human_delay(2.0, 3.5)
            else:
                print("[BOT] Warning: 'Work All' button image not found.")

            # Step 4: Close Heroes Modal
            close_screen = self.vision.capture_screen(force_refresh=True)
            close_match = self.vision.find_template(
                config.TARGET_IMAGES["close_button"], screen_gray=close_screen
            )
            if close_match:
                print(f"[BOT] Closing Heroes menu (Confidence: {close_match['confidence']:.2f})...")
                ActionEngine.click_match(close_match)
                self.vision.clear_cache()
                ActionEngine.human_delay(1.5, 2.5)

            # Step 5: Click screen center to collapse HUD menu
            center_x = screen.shape[1] // 2
            center_y = screen.shape[0] // 2
            print(f"[BOT] Clicking screen center ({center_x}, {center_y}) to collapse HUD menu...")
            ActionEngine.click_at(center_x, center_y)
            self.vision.clear_cache()
            ActionEngine.human_delay(1.5, 2.5)

            self.last_hero_work_time = time.time()
            self.update_progress()
            return True

        print("[BOT] Heroes button not visible on screen.")
        return False

    def enter_treasure_hunt(self) -> bool:
        """
        Ensures game is in Treasure Hunt mode.
        If DIRECT_LANDING_MODE is enabled, the direct URL lands straight into Treasure Hunt.
        Otherwise, attempts to locate and click the Treasure Hunt icon.
        """
        if config.DIRECT_LANDING_MODE:
            print("[BOT] Direct Treasure Hunt landing mode enabled. Skipping main menu icon click.")
            self.update_progress()
            return True

        screen = self.vision.capture_screen()
        th_match = self.vision.find_template(
            config.TARGET_IMAGES["treasure_hunt_icon"], screen_gray=screen
        )
        if th_match:
            print(
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
        print("[BOT] Scanning for Map Cleared indicators...")
        screen = self.vision.capture_screen()

        # Step 1: Check for map_complete_button first
        button_match = self.vision.find_template(
            config.TARGET_IMAGES["map_complete_button"], screen_gray=screen
        )
        if button_match:
            print(
                f"[BOT] 'Map Cleared' button detected (Confidence: {button_match['confidence']:.2f}). Transitioning map..."
            )
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
            print(
                f"[BOT] 'Map Cleared' modal detected (Confidence: {map_match['confidence']:.2f}). Transitioning map..."
            )
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
        print(f"\n--- [BOT CYCLE START - State: {self.state.name}] ---")

        # Invalidate frame cache at start of cycle
        self.vision.clear_cache()

        # Step 1: Check anti-stuck timeout recovery
        if self.check_stuck_timeout():
            self.handle_stuck_recovery()
            print("--- [BOT CYCLE END] ---\n")
            return

        # Step 2: Handle STUCK_RECOVERY state directly if set
        if self.state == BotState.STUCK_RECOVERY:
            self.handle_stuck_recovery()
            print("--- [BOT CYCLE END] ---\n")
            return

        # Step 3: Global Error & Disconnect scan
        if self.check_errors_or_disconnect():
            self.set_state(BotState.CHECKING_ERRORS)
            print("--- [BOT CYCLE END] ---\n")
            return

        # Step 4: Check Login requirement
        if self.handle_login():
            self.set_state(BotState.LOGGING_IN)
            print("--- [BOT CYCLE END] ---\n")
            return

        # Step 5: Check Map Cleared requirement
        if self.check_map_cleared():
            print("--- [BOT CYCLE END] ---\n")
            return

        # Step 6: FSM Work & Resting Cycle Logic
        if self.last_hero_work_time == 0:
            print("[BOT] Initial work cycle starting. Transitioning to SENDING_HEROES...")
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
                print(
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
                print(
                    f"[BOT] State: {self.state.name} | Heroes working/resting ({elapsed_str} elapsed). "
                    f"Next work cycle in {remaining_str}."
                )

                # Ensure we are inside Treasure Hunt map
                if self.state != BotState.RESTING and self.enter_treasure_hunt():
                    self.set_state(BotState.RESTING)

                # Execute anti-AFK idle jitter if resting
                self.check_idle_jitter()

        print("--- [BOT CYCLE END] ---\n")
