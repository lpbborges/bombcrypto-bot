from __future__ import annotations

import os
import sys


def is_windows() -> bool:
    return sys.platform == "win32"


def is_mac() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_wayland() -> bool:
    return is_linux() and (
        os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
        or "WAYLAND_DISPLAY" in os.environ
    )


def is_gnome() -> bool:
    if not is_linux():
        return False
    desktop = (
        os.environ.get("XDG_CURRENT_DESKTOP", "")
        + ":"
        + os.environ.get("DESKTOP_SESSION", "")
        + ":"
        + os.environ.get("GDMSESSION", "")
    ).lower()
    return "gnome" in desktop or "ubuntu" in desktop


def is_hyprland() -> bool:
    if not is_linux():
        return False
    desktop = (
        os.environ.get("XDG_CURRENT_DESKTOP", "") + ":" + os.environ.get("DESKTOP_SESSION", "")
    ).lower()
    return "hyprland" in desktop or "HYPRLAND_INSTANCE_SIGNATURE" in os.environ
