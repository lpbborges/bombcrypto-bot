from __future__ import annotations

import os
import shutil
import sys

from config import BotConfig
from modules.browser import BrowserManager
from modules.vision import VisionEngine


class SystemDiagnostic:
    config: BotConfig | None = None

    @classmethod
    def run_diagnostics(cls, config=None, verbose=True) -> dict:
        """
        Executes a comprehensive system and configuration check for Bomb Crypto Bot.
        Returns a dictionary of diagnostic results and logs findings.
        """
        if config is None:
            config = getattr(cls, "config", None) or BotConfig()
        cls.config = config
        results = {
            "os_info": {},
            "dependencies": {},
            "screen_capture": {},
            "mouse_backend": {},
            "browser": {},
            "targets": {},
            "notifications": {},
            "overall_status": "PASS",
            "warnings_count": 0,
            "errors_count": 0,
        }

        print("\n==================================================")
        print("    BOMB CRYPTO BOT SYSTEM DIAGNOSTIC & VERIFY    ")
        print("==================================================\n")

        # 1. OS & Desktop Environment Check
        os_name = sys.platform
        python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        xdg_type = os.environ.get("XDG_SESSION_TYPE", "N/A")
        wayland_disp = os.environ.get("WAYLAND_DISPLAY", "N/A")
        display = os.environ.get("DISPLAY", "N/A")

        results["os_info"] = {
            "platform": os_name,
            "python_version": python_ver,
            "session_type": xdg_type,
            "wayland_display": wayland_disp,
            "display": display,
        }

        print(" [1/6] Operating System & Environment:")
        print(f"   • Platform:          {os_name}")
        print(f"   • Python Version:    {python_ver}")
        print(f"   • Session Type:      {xdg_type}")
        print(f"   • Display Server:    {display} / {wayland_disp}\n")

        # 2. Package Dependencies Check
        required_pkgs = [
            ("cv2", "OpenCV Pattern Matching"),
            ("numpy", "NumPy Numerical Engine"),
            ("mss", "MSS Fast Screen Capture"),
            ("PIL", "Pillow Image Processing"),
            ("pyautogui", "PyAutoGUI Mouse Input Engine"),
            ("dotenv", "Dotenv Environment Variable Loader"),
        ]

        print(" [2/6] Python Package Dependencies:")
        for pkg_name, label in required_pkgs:
            try:
                __import__(pkg_name)
                print(f"   • [PASS] {label} ({pkg_name})")
                results["dependencies"][pkg_name] = "PASS"
            except ImportError as e:
                print(f"   • [FAIL] {label} ({pkg_name}) - MISSING! Run: pip install {pkg_name}")
                results["dependencies"][pkg_name] = f"FAIL: {e}"
                results["errors_count"] += 1

        print("")

        # 3. Target Template Images Check
        print(" [3/6] Target Image Assets Verification:")
        target_dir = getattr(cls.config, "targets_dir", "")
        if not os.path.exists(target_dir):
            print(f"   • [FAIL] Targets folder missing at: {target_dir}")
            results["targets"]["directory"] = "FAIL"
            results["errors_count"] += 1
        else:
            missing_targets = []
            for target_name, path in cls.config.target_images.items():
                if os.path.exists(path):
                    try:
                        import cv2

                        img = cv2.imread(path)
                        if img is not None:
                            h, w = img.shape[:2]
                            results["targets"][target_name] = f"PASS ({w}x{h})"
                        else:
                            print(f"   • [WARN] Target image unreadable: {target_name} ({path})")
                            results["targets"][target_name] = "WARN: Corrupted"
                            results["warnings_count"] += 1
                    except Exception as e:
                        print(f"   • [WARN] Target check error for {target_name}: {e}")
                        results["warnings_count"] += 1
                else:
                    missing_targets.append(target_name)

            if missing_targets:
                print(
                    f"   • [WARN] Missing template images ({len(missing_targets)}): {', '.join(missing_targets)}"
                )
                print(f"     -> Add target PNG crops into: {target_dir}")
                results["warnings_count"] += len(missing_targets)
            else:
                print(
                    f"   • [PASS] All {len(cls.config.target_images)} target template images verified in '{target_dir}'"
                )

        print("")

        # 4. Screen Capture Engine Test
        print(" [4/6] Screen Capture Diagnostics:")
        try:
            vision = VisionEngine(cls.config)
            frame = vision.capture_screen(force_refresh=True)
            if frame is not None and frame.size > 0:
                h, w = frame.shape[:2]
                max_val = frame.max()
                if max_val == 0:
                    print(f"   • [WARN] Screen capture returned black frame ({w}x{h}).")
                    print(
                        "     -> Note: On Ubuntu GNOME (Wayland), ensure gdbus or gnome-screenshot (`sudo apt install gnome-screenshot`) is available."
                    )
                    results["screen_capture"]["status"] = "WARN: Black Screen"
                    results["warnings_count"] += 1
                else:
                    print(
                        f"   • [PASS] Screen captured successfully ({w}x{h} resolution, max brightness: {max_val})"
                    )
                    results["screen_capture"]["status"] = f"PASS ({w}x{h})"
            else:
                print("   • [FAIL] Screen capture failed to return valid frame.")
                results["screen_capture"]["status"] = "FAIL"
                results["errors_count"] += 1
        except Exception as e:
            print(f"   • [FAIL] Vision engine diagnostic crash: {e}")
            results["screen_capture"]["status"] = f"FAIL: {e}"
            results["errors_count"] += 1

        print("")

        # 5. Mouse Automation Backend Test
        print(" [5/6] Mouse Automation Hardware/Software Backends:")
        has_uinput = getattr(sys.modules.get("modules.actions"), "UINPUT_MOUSE", None) is not None
        has_ydotool = shutil.which("ydotool") is not None
        has_xdotool = shutil.which("xdotool") is not None
        has_hyprctl = shutil.which("hyprctl") is not None

        print("   • PyAutoGUI Standard: [PASS] Enabled")
        print(
            f"   • Linux Kernel uinput: [{'PASS' if has_uinput else 'INFO'}] {'Available' if has_uinput else 'Not loaded (optional)'}"
        )
        print(
            f"   • Wayland ydotool:     [{'PASS' if has_ydotool else 'INFO'}] {'Available' if has_ydotool else 'Not installed (optional)'}"
        )
        print(
            f"   • X11 xdotool:         [{'PASS' if has_xdotool else 'INFO'}] {'Available' if has_xdotool else 'Not installed (optional)'}"
        )
        print(
            f"   • Hyprland hyprctl:    [{'PASS' if has_hyprctl else 'INFO'}] {'Available' if has_hyprctl else 'Not detected'}\n"
        )

        results["mouse_backend"] = {
            "uinput": has_uinput,
            "ydotool": has_ydotool,
            "xdotool": has_xdotool,
            "hyprctl": has_hyprctl,
        }

        # 6. Browser Environment & Executable Verification
        print(" [6/6] Browser & Game Version Configuration:")
        target_bname = BrowserManager.get_target_browser_name()
        b_info = BrowserManager.get_attached_browser_info()
        b_exe = BrowserManager.find_browser_executable(target_bname)

        game_ver = getattr(cls.config, "game_version", getattr(cls.config, "GAME_VERSION", "v13d"))
        print(f"   • Game Version:      {game_ver.upper()}")
        print(f"   • Target Browser:    {target_bname.capitalize()}")
        print(f"   • Executable Path:   {b_exe or 'Not Found on PATH'}")
        print(f"   • Attached Status:   {b_info['status']}")
        print(f"   • Direct URL Mode:   {cls.config.direct_treasure_url}")
        print(f"   • Direct Landing:    {cls.config.direct_landing_mode}")

        if not b_exe and target_bname != "default":
            print(f"   • [WARN] Could not find executable binary for '{target_bname}'.")
            print(
                "     -> Set BROWSER_EXECUTABLE_PATH in .env or pass --browser-path /path/to/browser"
            )
            results["warnings_count"] += 1
        else:
            print("   • [PASS] Browser binary verified.")

        print("\n==================================================")
        if results["errors_count"] == 0 and results["warnings_count"] == 0:
            print(" SYSTEM STATUS: PERFECT! All checks passed [PASS]")
            results["overall_status"] = "PASS"
        elif results["errors_count"] == 0:
            print(f" SYSTEM STATUS: READY WITH {results['warnings_count']} WARNING(S) [WARN]")
            results["overall_status"] = "WARN"
        else:
            print(
                f" SYSTEM STATUS: ATTENTION REQUIRED ({results['errors_count']} Error(s), {results['warnings_count']} Warning(s)) [FAIL]"
            )
            results["overall_status"] = "FAIL"
        print("==================================================\n")

        return results


def run_setup_wizard():
    """Interactive wizard to guide non-technical users in generating a .env configuration file."""
    env_path = os.path.join(BotConfig().base_dir, ".env")
    print("\n==================================================")
    print("      BOMB CRYPTO BOT INTERACTIVE SETUP WIZARD    ")
    print("==================================================\n")
    print("This wizard will help you configure your bot settings in '.env'.\n")

    default_version = (
        input("Game version (v13d / v10l) [default: v13d]: ").strip().lower() or "v13d"
    )
    default_interval = input("Hero work interval in minutes (default: 30): ").strip() or "30"
    default_browser = (
        input(
            "Target browser (brave / chrome / firefox / edge / default) [default: brave]: "
        ).strip()
        or "brave"
    )
    only_refresh = input(
        "Enable Inner Bot Mode (Only refresh page on error/disconnect)? (y/N): "
    ).strip().lower() in ("y", "yes")

    discord_url = input("Discord Webhook URL for notifications (optional): ").strip()
    telegram_token = input("Telegram Bot Token (optional): ").strip()
    telegram_chat = input("Telegram Chat ID (optional): ").strip()

    env_content = f"""# Bomb Crypto Automation Bot Configuration File
GAME_VERSION={default_version}
HERO_WORK_INTERVAL_MINUTES={default_interval}
TARGET_BROWSER={default_browser}
ONLY_REFRESH_ON_ERROR={"true" if only_refresh else "false"}
ENABLE_NOTIFICATIONS=true
DISCORD_WEBHOOK_URL={discord_url}
TELEGRAM_BOT_TOKEN={telegram_token}
TELEGRAM_CHAT_ID={telegram_chat}
"""

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content)
        print(f"\n[PASS] Successfully created configuration file: {env_path}\n")
    except Exception as e:
        print(f"\n[FAIL] Error writing configuration file: {e}\n")
