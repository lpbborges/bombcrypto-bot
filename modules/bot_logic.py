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
        Flexibly handles all login/reconnect permutations:
        - Direct refresh showing 'confirm_profile' ("OK") directly without 'connect_wallet'.
        - Full login flow: 'confirm_profile' -> 'connect_wallet' -> MetaMask sign -> 'confirm_profile'.
        """
        action_taken = False
        max_attempts = 4  # Process up to 4 sequential login interaction steps if needed

        for attempt in range(max_attempts):
            screen = self.vision.capture_screen()
            step_action = False

            # Check 1: Confirm profile ("OK" button)
            profile_ok = self.vision.find_template(config.TARGET_IMAGES["confirm_profile_ok"], screen_gray=screen)
            if profile_ok:
                print("[BOT] Confirm profile button ('OK') found. Clicking OK...")
                ActionEngine.click_match(profile_ok)
                ActionEngine.human_delay(3.0, 5.0)
                step_action = True

            # Check 2: Connect Wallet button
            connect_match = self.vision.find_template(config.TARGET_IMAGES["connect_wallet"], screen_gray=screen)
            if connect_match:
                print("[BOT] 'Connect Wallet' button found. Initiating login...")
                ActionEngine.click_match(connect_match)
                ActionEngine.human_delay(3.0, 5.0)
                step_action = True

            # Check 3: Select MetaMask wallet option
            wallet_select = self.vision.find_template(config.TARGET_IMAGES["select_metamask"], screen_gray=screen)
            if wallet_select:
                print("[BOT] Select MetaMask icon found. Clicking...")
                ActionEngine.click_match(wallet_select)
                ActionEngine.human_delay(3.0, 5.0)
                step_action = True

            # Check 4: MetaMask Sign popup button
            metamask_sign = self.vision.find_template(config.TARGET_IMAGES["metamask_sign"], screen_gray=screen)
            if metamask_sign:
                print("[BOT] MetaMask Sign button found. Signing transaction...")
                ActionEngine.click_match(metamask_sign)
                ActionEngine.human_delay(5.0, 8.0)
                step_action = True

            if step_action:
                action_taken = True
            else:
                # No remaining login elements found on screen
                break

        return action_taken

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
            print("[BOT] Found bottom arrow menu button. Opening menu...")
            ActionEngine.click_match(bottom_arrow_match)
            ActionEngine.human_delay(1.5, 3.0)
            screen = self.vision.capture_screen()
        else:
            print("[BOT] Bottom arrow menu button not found directly; checking if menu is already open...")

        # Step 2: Click Heroes Button inside opened menu
        heroes_match = self.vision.find_template(config.TARGET_IMAGES["heroes_button"], screen_gray=screen)
        if heroes_match:
            print("[BOT] Found Heroes button inside menu. Opening heroes list...")
            ActionEngine.click_match(heroes_match)
            ActionEngine.human_delay(2.0, 4.0)

            # Step 3: Click 'Work All' button inside heroes modal
            work_all_match = self.vision.find_template(config.TARGET_IMAGES["work_all_button"])
            if work_all_match:
                print("[BOT] Clicking 'Work All' button...")
                ActionEngine.click_match(work_all_match)
                ActionEngine.human_delay(1.5, 3.0)
            else:
                print("[BOT] Warning: 'Work All' button image not found.")

            # Step 4: Close Heroes Modal
            close_match = self.vision.find_template(config.TARGET_IMAGES["close_button"])
            if close_match:
                print("[BOT] Closing Heroes menu...")
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
