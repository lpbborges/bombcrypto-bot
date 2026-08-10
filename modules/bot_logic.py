import time
import config
from modules.vision import VisionEngine
from modules.actions import ActionEngine

class BombCryptoBot:
    def __init__(self):
        self.vision = VisionEngine()
        self.last_hero_work_time = 0

    def check_errors_or_disconnect(self):
        """
        Scans for common game error modals or disconnect OK buttons.
        Returns True if an error was handled or page refreshed.
        """
        print("[BOT] Scanning for error popups or disconnects...")
        screen = self.vision.capture_screen()

        # Check for 'OK' error button
        ok_match = self.vision.find_template(config.TARGET_IMAGES["error_ok"], screen_gray=screen)
        if ok_match:
            print("[BOT] Error popup detected. Clicking OK...")
            ActionEngine.click_match(ok_match)
            return True

        # Check for 'Unknown Error' modal
        unk_match = self.vision.find_template(config.TARGET_IMAGES["unknown_error"], screen_gray=screen)
        if unk_match:
            print("[BOT] Unknown error detected. Refreshing page...")
            ActionEngine.refresh_page()
            return True

        return False

    def handle_login(self):
        """
        Flexibly handles login/reconnect states without duplicate click spam.
        """
        screen = self.vision.capture_screen()

        # Step 1: Check for profile confirmation 'OK' button first
        profile_ok = self.vision.find_template(config.TARGET_IMAGES["confirm_profile_ok"], screen_gray=screen)
        if profile_ok:
            print(f"[BOT] Confirm profile button ('OK') found (Confidence: {profile_ok['confidence']:.2f}). Clicking OK...")
            ActionEngine.click_match(profile_ok)
            ActionEngine.human_delay(4.0, 6.0)
            return True

        # Step 2: Check for 'Connect Wallet' button
        connect_match = self.vision.find_template(config.TARGET_IMAGES["connect_wallet"], screen_gray=screen)
        if connect_match:
            print(f"[BOT] 'Connect Wallet' button found (Confidence: {connect_match['confidence']:.2f}). Initiating login...")
            ActionEngine.click_match(connect_match)
            ActionEngine.human_delay(4.0, 6.0)

            # Check if wallet selection modal pops up immediately after
            screen_after = self.vision.capture_screen()
            wallet_select = self.vision.find_template(config.TARGET_IMAGES["select_metamask"], screen_gray=screen_after)
            if wallet_select:
                print(f"[BOT] Select MetaMask icon found (Confidence: {wallet_select['confidence']:.2f}). Clicking...")
                ActionEngine.click_match(wallet_select)
                ActionEngine.human_delay(3.0, 5.0)

            # Check for MetaMask Sign button popup
            metamask_sign = self.vision.find_template(config.TARGET_IMAGES["metamask_sign"], screen_gray=screen_after)
            if metamask_sign:
                print(f"[BOT] MetaMask Sign button found (Confidence: {metamask_sign['confidence']:.2f}). Signing transaction...")
                ActionEngine.click_match(metamask_sign)
                ActionEngine.human_delay(5.0, 8.0)

            return True

        return False

    def send_heroes_to_work(self):
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
        bottom_arrow_match = self.vision.find_template(config.TARGET_IMAGES["bottom_arrow"], screen_gray=screen)
        if bottom_arrow_match:
            print(f"[BOT] Found bottom arrow menu button (Confidence: {bottom_arrow_match['confidence']:.2f}). Opening menu...")
            ActionEngine.click_match(bottom_arrow_match)
            ActionEngine.human_delay(2.0, 4.0)
            screen = self.vision.capture_screen()
        else:
            print("[BOT] Bottom arrow menu button not found directly; checking if menu is already open...")

        # Step 2: Click Heroes Button inside opened menu
        heroes_match = self.vision.find_template(config.TARGET_IMAGES["heroes_button"], screen_gray=screen)
        if heroes_match:
            print(f"[BOT] Found Heroes button inside menu (Confidence: {heroes_match['confidence']:.2f}). Opening heroes list...")
            ActionEngine.click_match(heroes_match)
            ActionEngine.human_delay(2.5, 4.5)

            # Step 3: Click 'Work All' button inside heroes modal
            work_all_match = self.vision.find_template(config.TARGET_IMAGES["work_all_button"])
            if work_all_match:
                print(f"[BOT] Clicking 'Work All' button (Confidence: {work_all_match['confidence']:.2f})...")
                ActionEngine.click_match(work_all_match)
                ActionEngine.human_delay(2.0, 3.5)
            else:
                print("[BOT] Warning: 'Work All' button image not found.")

            # Step 4: Close Heroes Modal
            close_match = self.vision.find_template(config.TARGET_IMAGES["close_button"])
            if close_match:
                print(f"[BOT] Closing Heroes menu (Confidence: {close_match['confidence']:.2f})...")
                ActionEngine.click_match(close_match)
                ActionEngine.human_delay(1.5, 2.5)

            self.last_hero_work_time = time.time()
            return True
        
        print("[BOT] Heroes button not visible on screen.")
        return False

    def enter_treasure_hunt(self):
        """
        Ensures game is in Treasure Hunt mode.
        If DIRECT_LANDING_MODE is enabled, the direct URL lands straight into Treasure Hunt.
        Otherwise, attempts to locate and click the Treasure Hunt icon.
        """
        if config.DIRECT_LANDING_MODE:
            print("[BOT] Direct Treasure Hunt landing mode enabled. Skipping main menu icon click.")
            return True

        screen = self.vision.capture_screen()
        th_match = self.vision.find_template(config.TARGET_IMAGES["treasure_hunt_icon"], screen_gray=screen)
        if th_match:
            print("[BOT] Found Treasure Hunt map icon. Entering map...")
            ActionEngine.click_match(th_match)
            ActionEngine.human_delay(2.0, 4.0)
            return True
        return False

    def run_cycle(self):
        """
        Main decision cycle for the bot.
        """
        print("\n--- [BOT CYCLE START] ---")
        
        # Step 1: Check for errors
        if self.check_errors_or_disconnect():
            return

        # Step 2: Check for login buttons
        if self.handle_login():
            return

        # Step 3: Check if it's time to send heroes to work
        elapsed_minutes = (time.time() - self.last_hero_work_time) / 60.0
        if self.last_hero_work_time == 0 or elapsed_minutes >= config.HERO_WORK_INTERVAL_MINUTES:
            print(f"[BOT] {elapsed_minutes:.1f} min elapsed since last work trigger. Sending heroes...")
            if self.send_heroes_to_work():
                self.enter_treasure_hunt()
        else:
            print(f"[BOT] Heroes working/resting. Next work trigger in {config.HERO_WORK_INTERVAL_MINUTES - elapsed_minutes:.1f} minutes.")

        # Step 4: Ensure we are inside Treasure Hunt map
        self.enter_treasure_hunt()
        print("--- [BOT CYCLE END] ---\n")
