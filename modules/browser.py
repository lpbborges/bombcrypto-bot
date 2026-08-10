import os
import shutil
import subprocess
import config

KNOWN_BRAVE_PATHS = [
    "/opt/brave.com/brave-origin-beta/brave",
    "/opt/brave.com/brave/brave",
    "/usr/bin/brave-browser",
    "/usr/bin/brave",
    "/usr/bin/brave-beta",
]

class BraveManager:
    @staticmethod
    def is_brave_running():
        """
        Checks if Brave browser processes are currently active on the system.
        """
        try:
            output = subprocess.check_output(["ps", "aux"], text=True)
            for line in output.splitlines():
                if "brave" in line.lower() and "grep" not in line.lower():
                    return True
        except Exception as e:
            print(f"[BROWSER] Warning checking process list: {e}")
        return False

    @staticmethod
    def find_brave_executable():
        """
        Finds the absolute path of the Brave browser binary on the system.
        """
        # Check known paths first
        for path in KNOWN_BRAVE_PATHS:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

        # Check system PATH
        for cmd in ["brave-browser", "brave", "brave-beta"]:
            found = shutil.which(cmd)
            if found:
                return found

        return None

    @staticmethod
    def launch_brave(url=config.DIRECT_TREASURE_URL):
        """
        Launches Brave browser with the direct game URL.
        """
        exe = BraveManager.find_brave_executable()
        if exe:
            print(f"[BROWSER] Launching Brave browser ({exe}) -> {url}")
            subprocess.Popen([exe, url])
            return True
        else:
            print("[BROWSER] Warning: Could not locate Brave executable binary on PATH.")
            return False

    @staticmethod
    def verify_and_ensure_brave():
        """
        Verifies Brave status. If Brave is not running, attempts to launch it automatically.
        """
        if BraveManager.is_brave_running():
            print("[BROWSER] Brave Browser detected and running.")
            return True

        print("[BROWSER] Brave Browser is not currently running. Attempting to launch...")
        return BraveManager.launch_brave()
