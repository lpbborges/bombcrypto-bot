from __future__ import annotations

import math
import os
import time
from enum import Enum, auto

import cv2
import numpy as np

from config import BotConfig
from modules.actions import ActionEngine
from modules.browser import BrowserManager
from modules.logger import logger
from modules.notifications import NotificationManager
from modules.vision import GameScreen, VisionEngine


def calculate_stamina_percentage(stamina_crop):
    """
    Calculates visual stamina bar fill percentage from crop, ignoring text/numbers in the center.
    Works on both grayscale and color arrays.
    """
    if stamina_crop is None or stamina_crop.size == 0:
        return 0.0
    if stamina_crop.ndim == 3:
        hsv = cv2.cvtColor(stamina_crop, cv2.COLOR_BGR2HSV)
        green_mask = cv2.inRange(hsv, (35, 70, 70), (85, 255, 255))
        col_has_green = np.sum(green_mask, axis=0) > 0
        return (np.sum(col_has_green) / stamina_crop.shape[1]) * 100.0
    else:
        # Grayscale array: green bar fill region (intensity 100-210)
        bright_mask = (stamina_crop >= 100) & (stamina_crop <= 210)
        col_has_bar = np.sum(bright_mask, axis=0) >= (stamina_crop.shape[0] * 0.35)
        return (np.sum(col_has_bar) / stamina_crop.shape[1]) * 100.0


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
    def __init__(self, cfg: BotConfig):
        self.config = cfg
        self.vision = VisionEngine(cfg)
        self.action = ActionEngine(cfg)
        self.state = BotState.INITIALIZING
        self.last_hero_work_time = 0
        self.last_progress_time = time.time()
        self.last_idle_jitter_time = 0
        self.last_periodic_refresh_time = time.time()
        self.start_time = time.time()

        # Auto-detect game version from open browser tab on initialization if auto configured
        if getattr(self.config, "game_version", "auto") == "auto":
            BrowserManager.sync_game_version_from_browser()

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

    def identify_current_screen(self, screen_gray=None):
        """
        Identifies the current game screen using VisionEngine template matching.

        Returns:
            tuple: (GameScreen, dict of matches)
        """
        screen_type, matches = self.vision.identify_screen(screen_gray=screen_gray)
        logger.info(f"[BOT SCREEN] Identified screen: {screen_type.name}")
        return screen_type, matches

    def determine_next_action(self, screen_gray=None):
        """
        Identifies the current screen and determines the appropriate next action.

        Returns:
            tuple: (GameScreen, action_name: str)
        """
        screen_type, matches = self.identify_current_screen(screen_gray=screen_gray)

        if screen_type == GameScreen.CAPTCHA:
            return screen_type, "handle_captcha"
        elif screen_type == GameScreen.ERROR_MODAL:
            return screen_type, "handle_error"
        elif screen_type in (
            GameScreen.LOGIN,
            GameScreen.METAMASK_SELECT,
            GameScreen.METAMASK_SIGN,
            GameScreen.CONFIRM_PROFILE,
        ):
            return screen_type, "handle_login"
        elif screen_type == GameScreen.MAP_CLEARED:
            return screen_type, "handle_map_cleared"
        elif screen_type == GameScreen.MAIN_MENU:
            return screen_type, "enter_treasure_hunt"
        elif screen_type == GameScreen.HEROES_MODAL:
            return screen_type, "process_heroes_modal"
        elif screen_type == GameScreen.TREASURE_HUNT_MAP:
            return screen_type, "in_game_monitoring"
        else:
            return GameScreen.UNKNOWN, "check_stuck_or_refresh"

    def handle_captcha(self) -> bool:
        """
        Handles captcha / security verification popup by notifying user via Discord/Telegram/logs.
        """
        logger.warning("[BOT CAPTCHA ALERT] Captcha or security check popup detected!")
        NotificationManager.send_notification(
            "Bomb Crypto Bot - Captcha Alert",
            "Captcha / Security verification detected on screen! Please solve it manually.",
            level="warning",
        )
        return True

    def set_state(self, new_state: BotState):
        """Transitions bot state with logging."""
        if self.state != new_state:
            logger.info(f"[BOT FSM] Transitioning state: {self.state.name} -> {new_state.name}")
            self.state = new_state

    def check_idle_jitter(self):
        """
        Executes anti-AFK idle jitter if bot is in RESTING state and interval has elapsed.
        """
        if getattr(self.config, "enable_idle_jitter", True) and self.state == BotState.RESTING:
            jitter_interval = getattr(self.config, "idle_jitter_interval_seconds", 30)
            if time.time() - self.last_idle_jitter_time >= jitter_interval:
                self.action.idle_jitter()
                self.last_idle_jitter_time = time.time()

    def update_progress(self):
        """Resets the anti-stuck timeout timer upon successful action/progression."""
        self.last_progress_time = time.time()

    def check_stuck_timeout(self) -> bool:
        """
        Checks if the bot has been stuck in the same unprogressive state beyond self.config.max_stuck_timeout_minutes.
        Triggers STUCK_RECOVERY state if timeout exceeded.
        """
        if self.state == BotState.STUCK_RECOVERY:
            return True

        stuck_duration = time.time() - self.last_progress_time
        max_stuck_seconds = self.config.max_stuck_timeout_minutes * 60.0

        if stuck_duration >= max_stuck_seconds:
            stuck_mins = stuck_duration / 60.0
            msg = (
                f"No progress detected for {stuck_mins:.1f} minutes "
                f"(exceeds threshold of {self.config.max_stuck_timeout_minutes} min). Triggering anti-stuck recovery..."
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
        self.action.refresh_page()
        self.vision.clear_cache()
        self.update_progress()
        self.last_periodic_refresh_time = time.time()
        self.set_state(BotState.INITIALIZING)

    def check_periodic_refresh(self) -> bool:
        """
        Checks if the configured periodic page refresh interval has elapsed.
        Refreshes browser page (or exits to menu & re-enters map on v10l) to prevent/recover stuck heroes when inner bot is active.
        """
        interval_mins = getattr(self.config, "refresh_interval_minutes", 0.0)
        if interval_mins <= 0:
            return False

        elapsed_seconds = time.time() - self.last_periodic_refresh_time
        interval_seconds = interval_mins * 60.0

        if elapsed_seconds >= interval_seconds:
            elapsed_str = format_duration(elapsed_seconds)
            logger.info(
                f"[BOT REFRESH] Periodic refresh interval reached ({elapsed_str} elapsed / {interval_mins:.1f} min threshold)."
            )
            NotificationManager.send_notification(
                "Bomb Crypto Bot Periodic Refresh",
                f"Refreshing page after {interval_mins:.1f}m interval to unstuck heroes.",
                level="info",
            )

            game_ver = getattr(self.config, "game_version", "v13d").lower()
            if game_ver == "v10l":
                logger.info("[BOT REFRESH] Executing v10l refresh...")
                screen = self.vision.capture_screen()
                back_match = self.vision.find_template(
                    self.config.target_images["back_button"], screen_gray=screen
                )
                if back_match:
                    logger.info(
                        f"[BOT REFRESH] Back button detected (Confidence: {back_match['confidence']:.2f}). Clicking back button..."
                    )
                    self.action.click_match(back_match)
                    self.vision.clear_cache()
                    self.action.human_delay(2.0, 4.0)

                entered = self.enter_treasure_hunt()
                if not back_match and not entered:
                    logger.info(
                        "[BOT REFRESH] Neither back button nor Treasure Hunt button found. Refreshing browser page..."
                    )
                    self.action.refresh_page()
            else:
                self.action.refresh_page()

            self.vision.clear_cache()
            self.update_progress()
            self.last_periodic_refresh_time = time.time()
            self.set_state(BotState.INITIALIZING)
            return True

        return False

    def check_errors_or_disconnect(self) -> bool:
        """
        Scans for common game error modals (error_message/unknown_error)
        or error OK button (error_ok).
        Returns True if an error was handled or page refreshed.
        """
        logger.info("[BOT] Scanning for error popups or disconnects...")
        screen = self.vision.capture_screen()

        # Check for 'OK' error button (error_ok)
        ok_match = self.vision.find_template(
            self.config.target_images["error_ok"], screen_gray=screen
        )

        if ok_match:
            logger.info(
                f"[BOT] Error popup OK button detected (Confidence: {ok_match['confidence']:.2f}). Clicking OK..."
            )
            self.errors_cleared_count += 1
            NotificationManager.notify_error_cleared("Error OK Button")
            self.action.click_match(ok_match)
            self.vision.clear_cache()
            self.update_progress()
            return True

        # Check for error message modal (error_message or unknown_error)
        err_msg_match = self.vision.find_template(
            self.config.target_images["error_message"], screen_gray=screen
        ) or self.vision.find_template(
            self.config.target_images["unknown_error"], screen_gray=screen
        )

        if err_msg_match:
            logger.info(
                f"[BOT] Error message modal detected (Confidence: {err_msg_match['confidence']:.2f})."
            )
            self.errors_cleared_count += 1
            # Try to see if an OK button is present to dismiss the error message modal
            ok_match = self.vision.find_template(
                self.config.target_images["error_ok"], screen_gray=screen
            )

            if ok_match:
                logger.info("[BOT] Found OK button for error message. Clicking OK...")
                NotificationManager.notify_error_cleared("Error Message OK Button")
                self.action.click_match(ok_match)
            else:
                logger.info("[BOT] No OK button found for error message modal. Refreshing page...")
                NotificationManager.notify_error_cleared("Error Message Modal")
                self.action.refresh_page()
                self.last_periodic_refresh_time = time.time()

            self.vision.clear_cache()
            self.update_progress()
            return True

        return False

    def handle_login(self) -> bool:
        """Flexibly handles login/reconnect states without duplicate click spam."""
        screen = self.vision.capture_screen()
        if self._try_confirm_profile(screen):
            return True
        if self._try_metamask_sign(screen):
            return True
        if self._try_metamask_select(screen):
            return True
        if self._try_connect_wallet(screen):
            return True
        return False

    def _try_confirm_profile(self, screen) -> bool:
        profile_ok = self.vision.find_template(
            self.config.target_images["confirm_profile_ok"], screen_gray=screen
        )
        if profile_ok:
            logger.info("[BOT] Confirm profile button ('OK') found. Clicking OK...")
            self.action.click_match(profile_ok)
            self.vision.clear_cache()
            self.action.human_delay(4.0, 6.0)
            self.update_progress()
            return True
        return False

    def _try_metamask_sign(self, screen) -> bool:
        metamask_sign = self.vision.find_template(
            self.config.target_images["metamask_sign"], screen_gray=screen
        )
        if metamask_sign:
            logger.info("[BOT] MetaMask Sign/Confirm button found. Signing transaction...")
            self.action.click_match(metamask_sign)
            self.vision.clear_cache()
            self.action.human_delay(5.0, 8.0)
            self.update_progress()
            return True
        return False

    def _try_metamask_select(self, screen) -> bool:
        wallet_select = self.vision.find_template(
            self.config.target_images["select_metamask"], screen_gray=screen
        )
        if wallet_select:
            logger.info("[BOT] Select MetaMask icon found. Clicking...")
            self.action.click_match(wallet_select)
            self.vision.clear_cache()
            self.action.human_delay(3.0, 5.0)
            self.update_progress()
            return True
        return False

    def _try_connect_wallet(self, screen) -> bool:
        connect_match = self.vision.find_template(
            self.config.target_images["connect_wallet"], screen_gray=screen
        )
        if connect_match:
            logger.info("[BOT] 'Connect Wallet' button found. Initiating login...")
            self.action.click_match(connect_match)
            self.vision.clear_cache()
            self.action.human_delay(4.0, 6.0)
            self.update_progress()

            screen_after = self.vision.capture_screen(force_refresh=True)
            self._try_metamask_select(screen_after)

            screen_after_sign = self.vision.capture_screen(force_refresh=True)
            self._try_metamask_sign(screen_after_sign)
            return True
        return False

    def _scan_and_work_eligible_heroes(
        self,
        scroll_pass: int,
        min_stamina: float,
        stamina_targets: list[tuple[str, float]],
        enable_home: bool,
        tier_targets: list[tuple[str, str, int]],
        all_home_candidates: list[dict],
    ) -> int:
        """Processes a single scroll pass during hero work scanning."""
        work_all_screen_color = self.vision.capture_screen_color(force_refresh=True)
        work_all_screen = self._convert_to_gray(work_all_screen_color)

        work_button_matches = self._find_work_button_matches(work_all_screen)
        stamina_matches = self._find_stamina_matches(work_all_screen, stamina_targets)

        eligible_clicks = self._calculate_eligible_clicks(
            work_button_matches, stamina_matches, work_all_screen_color, min_stamina
        )

        sent_count = self._execute_clicks(eligible_clicks, scroll_pass, min_stamina)

        if (
            enable_home
            and "available_home" in self.config.target_images
            and os.path.exists(self.config.target_images["available_home"])
        ):
            if sent_count > 0:
                work_all_screen_color = self.vision.capture_screen_color(force_refresh=True)
                work_all_screen = self._convert_to_gray(work_all_screen_color)
            self._scan_home_candidates(
                work_all_screen, tier_targets, all_home_candidates, scroll_pass
            )

        return sent_count

    def _convert_to_gray(self, screen_color):
        if screen_color.ndim == 3:
            return cv2.cvtColor(screen_color, cv2.COLOR_BGR2GRAY)
        return screen_color

    def _find_work_button_matches(self, screen_gray):
        if "work_button" in self.config.target_images and os.path.exists(
            self.config.target_images["work_button"]
        ):
            return self.vision.find_unique_matches(
                self.config.target_images["work_button"],
                screen_gray=screen_gray,
                threshold=0.65,
                min_distance=25,
            )
        return []

    def _find_stamina_matches(self, screen_gray, stamina_targets):
        stamina_paths = [t[0] for t in stamina_targets if os.path.exists(t[0])]
        min_dist = getattr(self.config, "stamina_min_distance", 30)

        if stamina_paths:
            return self.vision.find_unique_matches(
                stamina_paths, screen_gray=screen_gray, threshold=0.82, min_distance=min_dist
            )

        fallback_paths = [
            self.config.target_images[k]
            for k in ["full_bar", "80_bar"]
            if k in self.config.target_images and os.path.exists(self.config.target_images[k])
        ]
        return self.vision.find_unique_matches(
            fallback_paths, screen_gray=screen_gray, min_distance=min_dist
        )

    def _calculate_eligible_clicks(self, work_buttons, stamina_matches, screen_color, min_stamina):
        eligible = []
        if work_buttons:
            for w_btn in work_buttons:
                w_x, w_y = w_btn["x"], w_btn["y"]
                has_bar = any(
                    abs(s["y"] - w_y) <= getattr(self.config, "stamina_y_tolerance", 25)
                    and s["x"] < w_x
                    for s in stamina_matches
                )

                c_xmin = max(0, w_x - getattr(self.config, "stamina_crop_xmin_offset", 180))
                c_xmax = max(0, w_x - getattr(self.config, "stamina_crop_xmax_offset", 45))
                c_ymin = max(0, w_y - getattr(self.config, "stamina_crop_y_offset", 18))
                c_ymax = min(
                    screen_color.shape[0], w_y + getattr(self.config, "stamina_crop_y_offset", 18)
                )

                crop = screen_color[c_ymin:c_ymax, c_xmin:c_xmax]
                pct = calculate_stamina_percentage(crop)

                if pct >= (min_stamina - 2.0) or has_bar:
                    eligible.append((w_x, w_y))
        elif stamina_matches:
            for s_m in stamina_matches:
                eligible.append((s_m["x"] + 140, s_m["y"]))

        unique = []
        for x, y in eligible:
            if not any(math.hypot(x - u_x, y - u_y) < 20 for u_x, u_y in unique):
                unique.append((x, y))
        return unique

    def _execute_clicks(self, clicks, scroll_pass, min_stamina):
        if not clicks:
            return 0
        logger.info(
            f"[BOT] Pass {scroll_pass + 1}: Found {len(clicks)} eligible hero(es) with stamina >= {min_stamina:.0f}%."
        )
        for x, y in clicks:
            self.action.click_at(x, y)
            self.action.human_delay(0.5, 1.2)
        self.vision.clear_cache()
        self.action.human_delay(1.0, 2.0)
        return len(clicks)

    def _scan_home_candidates(self, screen_gray, tier_targets, all_home_candidates, scroll_pass):
        remaining_work = self._find_work_button_matches(screen_gray)
        home_buttons = self.vision.find_unique_matches(
            self.config.target_images["available_home"],
            screen_gray=screen_gray,
            threshold=0.75,
            min_distance=25,
        )

        if not home_buttons or not remaining_work:
            return

        all_tier_matches = []
        for path, name, prio in tier_targets:
            if os.path.exists(path):
                matches = self.vision.find_unique_matches(
                    path, screen_gray=screen_gray, threshold=0.70, min_distance=20
                )
                for m in matches:
                    m.update({"tier_name": name, "priority": prio})
                    all_tier_matches.append(m)

        for h_btn in home_buttons:
            h_y = h_btn["y"]
            if not any(abs(w["y"] - h_y) <= 25 for w in remaining_work):
                continue

            tier = next((tm for tm in all_tier_matches if abs(tm["y"] - h_y) <= 30), None)
            if tier and tier["priority"] > 0:
                all_home_candidates.append(
                    {
                        "priority": tier["priority"],
                        "tier_name": tier["tier_name"],
                        "pass": scroll_pass,
                        "x": h_btn["x"],
                        "y": h_y,
                    }
                )

    def _execute_home_strategy(
        self, max_scroll_passes: int, all_home_candidates: list[dict], screen_shape: tuple
    ) -> int:
        """Executes Phase 2 global home placement across modal scroll passes."""
        self._prepare_home_candidates(all_home_candidates)
        self._scroll_to_top(max_scroll_passes, screen_shape)
        return self._process_home_passes(max_scroll_passes, all_home_candidates, screen_shape)

    def _prepare_home_candidates(self, all_home_candidates: list[dict]):
        all_home_candidates.sort(key=lambda c: c["priority"], reverse=True)
        logger.info(
            f"[BOT] Full menu scan complete. Discovered {len(all_home_candidates)} resting high-tier candidate(s) for home."
        )

    def _scroll_to_top(self, max_scroll_passes: int, screen_shape: tuple):
        center_x = screen_shape[1] // 2
        center_y = screen_shape[0] // 2
        for _ in range(max_scroll_passes - 1):
            self.action.scroll_up(center_x, center_y, clicks=5)
            time.sleep(0.1)
        self.vision.clear_cache()
        self.action.human_delay(1.5, 2.5)

    def _process_home_passes(
        self, max_scroll_passes: int, all_home_candidates: list[dict], screen_shape: tuple
    ) -> int:
        total_sent_home = 0
        home_full = False
        center_x = screen_shape[1] // 2
        center_y = screen_shape[0] // 2

        for target_pass in range(max_scroll_passes):
            if home_full:
                break

            pass_candidates = [c for c in all_home_candidates if c["pass"] == target_pass]
            if pass_candidates:
                sent, home_full = self._process_home_candidates_on_pass(pass_candidates)
                total_sent_home += sent

            if target_pass < max_scroll_passes - 1:
                self.action.scroll_down(center_x, center_y, clicks=5)
                self.vision.clear_cache()
                self.action.human_delay(1.5, 2.5)

        return total_sent_home

    def _process_home_candidates_on_pass(self, pass_candidates: list[dict]) -> tuple[int, bool]:
        pass_screen = self.vision.capture_screen(force_refresh=True)
        home_button_matches = self.vision.find_unique_matches(
            self.config.target_images["available_home"],
            screen_gray=pass_screen,
            threshold=0.75,
            min_distance=25,
        )

        home_full = False
        if (
            not home_button_matches
            and "without_space_home" in self.config.target_images
            and os.path.exists(self.config.target_images["without_space_home"])
        ):
            if self.vision.find_template(
                self.config.target_images["without_space_home"], screen_gray=pass_screen
            ):
                logger.info("[BOT] Home is full or unavailable.")
                home_full = True

        sent = 0
        if home_button_matches and not home_full:
            for cand in pass_candidates:
                matched_btn = next(
                    (b for b in home_button_matches if abs(b["y"] - cand["y"]) <= 25), None
                )
                click_x = matched_btn["x"] if matched_btn else cand["x"]
                click_y = matched_btn["y"] if matched_btn else cand["y"]

                self.action.click_at(click_x, click_y)
                sent += 1
                logger.info(f"[BOT] Placed {cand['tier_name']} hero at home.")
                self.action.human_delay(0.5, 1.2)

            self.vision.clear_cache()
            self.action.human_delay(1.0, 2.0)

        return sent, home_full

    def _close_heroes_modal(self, screen_shape: tuple) -> None:
        """Closes Heroes modal menu and clicks screen center."""
        close_screen = self.vision.capture_screen(force_refresh=True)
        close_match = self.vision.find_template(
            self.config.target_images["close_button"], screen_gray=close_screen
        )
        if close_match:
            logger.info(
                f"[BOT] Closing Heroes menu (Confidence: {close_match['confidence']:.2f})..."
            )
            self.action.click_match(close_match)
            self.vision.clear_cache()
            self.action.human_delay(1.5, 2.5)

        center_x = screen_shape[1] // 2
        center_y = screen_shape[0] // 2
        logger.info(
            f"[BOT] Clicking screen center ({center_x}, {center_y}) to collapse HUD menu..."
        )
        self.action.click_at(center_x, center_y)
        self.vision.clear_cache()
        self.action.human_delay(1.5, 2.5)

    def send_heroes_to_work(self) -> bool:
        """
        Sequence:
        1. Click the bottom arrow to expand the bottom menu.
        2. Click 'heroes_button' inside the opened menu.
        3. Click 'Work All' or select heroes by stamina inside the heroes modal.
        4. Click close modal button ('X').
        """
        logger.info("[BOT] Attempting to send heroes to work...")
        screen = self.vision.capture_screen()

        screen = self._open_bottom_menu(screen)

        if not self._open_heroes_menu(screen):
            logger.info("[BOT] Heroes button not visible on screen.")
            return False

        if (
            getattr(self.config, "work_only_stamina", True)
            or getattr(self.config, "hero_work_mode", "stamina") != "all"
        ):
            self._process_heroes_by_stamina(screen)
        else:
            self._process_work_all_heroes()

        self._close_heroes_modal(screen.shape)

        self.last_hero_work_time = time.time()
        self.hero_work_cycles_count += 1
        self.update_progress()
        NotificationManager.notify_hero_cycle("Heroes sent to work successfully.")
        return True

    def _open_bottom_menu(self, screen):
        bottom_arrow_match = self.vision.find_template(
            self.config.target_images["bottom_arrow"], screen_gray=screen
        )
        if bottom_arrow_match:
            logger.info("[BOT] Found bottom arrow menu button. Opening menu...")
            self.action.click_match(bottom_arrow_match)
            self.vision.clear_cache()
            self.action.human_delay(2.0, 4.0)
            return self.vision.capture_screen(force_refresh=True)
        else:
            logger.info(
                "[BOT] Bottom arrow menu button not found directly; checking if menu is already open..."
            )
            return screen

    def _open_heroes_menu(self, screen) -> bool:
        heroes_match = self.vision.find_template(
            self.config.target_images["heroes_button"], screen_gray=screen
        )
        if heroes_match:
            logger.info("[BOT] Found Heroes button inside menu. Opening heroes list...")
            self.action.click_match(heroes_match)
            self.vision.clear_cache()
            self.action.human_delay(2.5, 4.5)
            return True
        return False

    def _process_heroes_by_stamina(self, screen):
        min_stamina = getattr(self.config, "hero_min_stamina", 60.0)
        max_scroll_passes = getattr(self.config, "hero_modal_max_scrolls", 4)
        enable_home = getattr(self.config, "enable_home_strategy", True)
        logger.info(f"[BOT] Scanning hero list for stamina >= {min_stamina:.0f}%...")

        stamina_targets = self.config.load_stamina_targets(min_stamina)
        tier_targets = self.config.load_tier_targets() if enable_home else []
        total_sent = 0
        all_home_candidates = []

        for scroll_pass in range(max_scroll_passes):
            sent = self._scan_and_work_eligible_heroes(
                scroll_pass,
                min_stamina,
                stamina_targets,
                enable_home,
                tier_targets,
                all_home_candidates,
            )
            total_sent += sent
            if scroll_pass < max_scroll_passes - 1:
                center_x = screen.shape[1] // 2
                center_y = screen.shape[0] // 2
                self.action.scroll_down(center_x, center_y, clicks=5)
                self.vision.clear_cache()
                self.action.human_delay(1.5, 2.5)

        if total_sent > 0:
            logger.info(f"[BOT] Sent a total of {total_sent} hero(es) to work.")
        else:
            logger.warning(f"[BOT] No heroes with stamina >= {min_stamina:.0f}% found in list.")

        if enable_home and all_home_candidates:
            total_home = self._execute_home_strategy(
                max_scroll_passes, all_home_candidates, screen.shape
            )
            if total_home > 0:
                logger.info(f"[BOT] Sent a total of {total_home} hero(es) to home.")

    def _process_work_all_heroes(self):
        work_all_screen = self.vision.capture_screen(force_refresh=True)
        rest_all_match = self.vision.find_template(
            self.config.target_images["rest_all_button"], screen_gray=work_all_screen
        )
        if rest_all_match:
            logger.info(
                "[BOT] 'Rest All' button detected. All heroes are already working, taking no action."
            )
        else:
            work_all_match = self.vision.find_template(
                self.config.target_images["work_all_button"], screen_gray=work_all_screen
            )
            if work_all_match:
                logger.info("[BOT] Clicking 'Work All' button...")
                self.action.click_match(work_all_match)
                self.vision.clear_cache()
                self.action.human_delay(2.0, 3.5)
            else:
                logger.warning("[BOT] Neither 'Work All' nor 'Rest All' button image found.")

    def enter_treasure_hunt(self) -> bool:
        """
        Ensures game is in Treasure Hunt mode.
        If DIRECT_LANDING_MODE is enabled (default for v13d), the direct URL lands straight into Treasure Hunt.
        Otherwise (default for v10l), attempts to locate and click the Treasure Hunt icon on the main menu.
        """
        if self.config.direct_landing_mode:
            logger.info("[BOT] Direct landing mode active. Skipping main menu icon click.")
            self.update_progress()
            return True

        logger.info("[BOT] Searching for Treasure Hunt icon on main menu...")
        screen = self.vision.capture_screen()
        th_match = self.vision.find_template(
            self.config.target_images["treasure_hunt_icon"], screen_gray=screen
        )
        if not th_match and "treasure_hunt_button" in self.config.target_images:
            th_match = self.vision.find_template(
                self.config.target_images["treasure_hunt_button"], screen_gray=screen
            )

        if th_match:
            logger.info(
                f"[BOT] Found Treasure Hunt map icon (Confidence: {th_match['confidence']:.2f}). Clicking to enter map..."
            )
            self.action.click_match(th_match)
            self.vision.clear_cache()
            self.action.human_delay(2.0, 4.0)
            self.update_progress()
            return True

        logger.info("[BOT] Treasure Hunt icon not found on current screen.")
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
            self.config.target_images["map_complete_button"], screen_gray=screen
        )
        if button_match:
            logger.info(
                f"[BOT] 'Map Cleared' button detected (Confidence: {button_match['confidence']:.2f}). Transitioning map..."
            )
            self.maps_cleared_count += 1
            NotificationManager.notify_map_cleared()
            self.set_state(BotState.MAP_CLEARED)
            self.action.click_match(button_match)
            self.vision.clear_cache()
            self.action.human_delay(3.0, 5.0)
            self.update_progress()
            self.set_state(BotState.RESTING)
            return True

        # Step 2: Check for map_complete modal as fallback
        map_match = self.vision.find_template(
            self.config.target_images["map_complete"], screen_gray=screen
        )
        if map_match:
            logger.info(
                f"[BOT] 'Map Cleared' modal detected (Confidence: {map_match['confidence']:.2f}). Transitioning map..."
            )
            self.maps_cleared_count += 1
            NotificationManager.notify_map_cleared()
            self.set_state(BotState.MAP_CLEARED)
            self.action.click_match(map_match)
            self.vision.clear_cache()
            self.action.human_delay(3.0, 5.0)
            self.update_progress()
            self.set_state(BotState.RESTING)
            return True

        return False

    def run_cycle(self):
        """FSM-driven main decision cycle for the bot."""
        self.cycles_completed += 1
        logger.info(
            f"--- [BOT CYCLE #{self.cycles_completed} START - State: {self.state.name}] ---"
        )
        logger.debug(f"[METRICS] {self.get_stats_summary()}")
        BrowserManager.focus_game_window()
        self.vision.clear_cache()

        if self.check_stuck_timeout() or self.state == BotState.STUCK_RECOVERY:
            self.handle_stuck_recovery()
            logger.info("--- [BOT CYCLE END] ---")
            return

        screen_type, action_name = self.determine_next_action()
        logger.info(f"[BOT DECISION] Screen: {screen_type.name} -> Next Action: {action_name}")

        if self._execute_screen_action(screen_type, action_name):
            logger.info("--- [BOT CYCLE END] ---")
            return

        if self.check_periodic_refresh():
            logger.info("--- [BOT CYCLE END] ---")
            return

        if screen_type == GameScreen.UNKNOWN and self._handle_unknown_screen():
            logger.info("--- [BOT CYCLE END] ---")
            return

        self._execute_fsm_work_cycle()
        logger.info("--- [BOT CYCLE END] ---")

    def _execute_screen_action(self, screen_type, action_name) -> bool:
        if action_name == "handle_captcha":
            self.handle_captcha()
            return True
        if action_name == "handle_error":
            self.set_state(BotState.CHECKING_ERRORS)
            self.check_errors_or_disconnect()
            return True
        if action_name == "handle_login":
            self.set_state(BotState.LOGGING_IN)
            self.handle_login()
            return True
        if action_name == "handle_map_cleared":
            self.check_map_cleared()
            return True
        if action_name == "enter_treasure_hunt":
            if self.enter_treasure_hunt():
                self.set_state(BotState.RESTING)
            return True
        return False

    def _handle_unknown_screen(self) -> bool:
        if self.check_errors_or_disconnect():
            self.set_state(BotState.CHECKING_ERRORS)
            return True
        if self.handle_login():
            self.set_state(BotState.LOGGING_IN)
            return True
        if self.check_map_cleared():
            return True
        return False

    def _execute_fsm_work_cycle(self):
        only_error_refresh = getattr(self.config, "only_refresh_on_error", False)
        hero_work_enabled = getattr(self.config, "enable_hero_work_actions", True)

        if only_error_refresh or not hero_work_enabled:
            mode_desc = "Error-Only Refresh" if only_error_refresh else "Inner Bot Monitoring"
            logger.info(
                f"[BOT] State: {self.state.name} | Inner Bot active ({mode_desc}). Monitoring for errors or stuck state..."
            )
            if self.state != BotState.RESTING and self.enter_treasure_hunt():
                self.set_state(BotState.RESTING)
            self.check_idle_jitter()
        else:
            self._handle_active_hero_work()

    def _handle_active_hero_work(self):
        if self.last_hero_work_time == 0:
            logger.info("[BOT] Initial work cycle starting. Transitioning to SENDING_HEROES...")
            self._transition_and_send_heroes()
        else:
            elapsed_seconds = time.time() - self.last_hero_work_time
            interval_seconds = self.config.hero_work_interval_minutes * 60.0

            if elapsed_seconds >= interval_seconds:
                elapsed_str = format_duration(elapsed_seconds)
                logger.info(
                    f"[BOT] Work interval reached ({elapsed_str} elapsed). Transitioning to SENDING_HEROES..."
                )
                self._transition_and_send_heroes()
            else:
                self._wait_for_next_cycle(elapsed_seconds, interval_seconds)

    def _transition_and_send_heroes(self):
        self.set_state(BotState.SENDING_HEROES)
        if self.send_heroes_to_work():
            self.set_state(BotState.ENTERING_MAP)
            self.enter_treasure_hunt()
            self.set_state(BotState.RESTING)

    def _wait_for_next_cycle(self, elapsed_seconds, interval_seconds):
        remaining_seconds = interval_seconds - elapsed_seconds
        elapsed_str = format_duration(elapsed_seconds)
        remaining_str = format_duration(remaining_seconds)
        logger.info(
            f"[BOT] State: {self.state.name} | Heroes working/resting ({elapsed_str} elapsed). Next work cycle in {remaining_str}."
        )

        if self.state != BotState.RESTING and self.enter_treasure_hunt():
            self.set_state(BotState.RESTING)
        self.check_idle_jitter()
