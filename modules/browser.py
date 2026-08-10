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
    "/snap/bin/brave",
    "/snap/bin/brave-browser",
]


class BraveManager:
    @staticmethod
    def get_attached_browser_info():
        """
        Detects active browser processes and returns details about the attached browser.

        Returns:
            dict: { 'name': str, 'pid': str, 'exe': str, 'status': str }
        """
        browser_targets = [
            (
                "Brave Browser (Beta/Release)",
                ["brave-origin-beta", "brave-browser", "brave"],
            ),
            ("Google Chrome", ["google-chrome", "chrome", "chromium"]),
            ("Mozilla Firefox", ["firefox"]),
            ("Microsoft Edge", ["msedge", "edge"]),
        ]
        ignore_terms = [
            "crashpad",
            "renderer",
            "utility",
            "zygote",
            "sandbox",
            "type=",
            "grep",
        ]

        try:
            output = subprocess.check_output(["ps", "-eo", "pid,comm,args"], text=True)
            for name, keywords in browser_targets:
                for line in output.splitlines():
                    line_lower = line.lower()
                    if any(k in line_lower for k in keywords) and not any(
                        term in line_lower for term in ignore_terms
                    ):
                        parts = line.strip().split(None, 2)
                        if len(parts) >= 3:
                            pid, _, args = parts[0], parts[1], parts[2]
                            exe_path = args.split()[0]
                            return {
                                "name": name,
                                "pid": pid,
                                "exe": exe_path,
                                "status": "ATTACHED & RUNNING",
                            }
        except Exception as e:
            print(f"[BROWSER] Warning querying process table: {e}")

        # If brave executable is found on system but not currently running
        exe = BraveManager.find_brave_executable()
        if exe:
            return {
                "name": "Brave Browser",
                "pid": "N/A",
                "exe": exe,
                "status": "NOT RUNNING (Auto-launch enabled)",
            }

        return {
            "name": "Unknown / Manual Browser",
            "pid": "N/A",
            "exe": "N/A",
            "status": "WAITING FOR BROWSER",
        }

    @staticmethod
    def is_brave_running():
        """
        Checks if Brave browser processes are currently active on the system.
        """
        info = BraveManager.get_attached_browser_info()
        return "Brave" in info.get("name", "") and info.get("status") == "ATTACHED & RUNNING"

    @staticmethod
    def find_brave_executable():
        """
        Finds the absolute path of the Brave browser binary on the system.
        """
        for path in KNOWN_BRAVE_PATHS:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

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
        info = BraveManager.get_attached_browser_info()
        if info["status"] == "ATTACHED & RUNNING":
            return True

        print("[BROWSER] Brave Browser is not currently running. Launching Brave automatically...")
        return BraveManager.launch_brave()
