# Bomb Crypto Automation Bot v2.2.0

A robust, multi-platform, computer-vision-powered Python bot for **Bomb Crypto** (https://game.bombcrypto.io/).

Engineered to be **easy to use** and **work across different operating systems (Linux X11/Wayland, Windows, macOS)**, screen resolutions, and web browsers (Brave, Chrome, Firefox, Edge, or System Default).

---

## 🌟 Key Features & Improvements

- **Multi-OS & Desktop Support**: Works on Linux (X11 & Wayland), Windows, and macOS.
- **Multi-Browser Integration**: Native auto-launch and process tracking for **Brave**, **Google Chrome**, **Mozilla Firefox**, **Microsoft Edge**, **Opera**, **Vivaldi**, or **System Default Browser**.
- **System Self-Diagnostic Suite (`python main.py --check`)**: Verifies Python dependencies, display server permissions, screen capture resolution, mouse automation backends, and target image integrity.
- **Interactive Setup Wizard (`python main.py --setup`)**: Step-by-step terminal wizard to easily create and configure your `.env` settings file.
- **Advanced Vision Matching Engine**: Multi-scale OpenCV pattern matching (0.50x to 1.50x) supporting standard 1080p, 1440p, 4K, and HiDPI/Retina display scaling.
- **Anti-Detection & Humanized Controls**: Non-linear cubic Bézier mouse movement trajectories, Gaussian reaction delays, anti-AFK idle mouse jitters, and uinput/ydotool/xdotool mouse input backends.
- **Multi-Channel Notifications**: Real-time Discord Webhooks and Telegram Bot alerts for work cycles, cleared errors, completed maps, and anti-stuck recoveries.

---

## 📂 Project Structure

```
bombcrypto-bot/
├── config.py             # Global configuration defaults & env variable loading
├── main.py               # Main CLI entry point & bot loop execution
├── .env.example          # Environment configuration template
├── pyproject.toml        # Project metadata and linting configuration
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development & test dependencies
├── modules/
│   ├── __init__.py
│   ├── actions.py        # Cross-platform mouse & keyboard automation engine
│   ├── bot_logic.py      # Finite State Machine (FSM) & stats tracker
│   ├── browser.py        # Multi-OS browser process detector & launcher
│   ├── diagnostics.py    # Self-test diagnostic engine & interactive setup wizard
│   ├── logger.py         # Colorized ANSI console & file logging engine
│   ├── notifications.py  # Discord Webhook & Telegram alert manager
│   └── vision.py         # Multi-scale OpenCV template matching & screen grab
├── targets/              # Template PNG images for game buttons & modals
└── tests/                # Automated unit test suite (57+ unit tests)
```

---

## 🚀 Quick Start Guide

### 1. Install Dependencies

Ensure Python 3.8+ is installed on your system. Run:

```bash
cd bombcrypto-bot
pip install -r requirements.txt
```

### 2. Verify Your System Setup

Run the built-in diagnostic test to verify display, screen grab, mouse engine, and target images:

```bash
python main.py --check
```

*Or run the interactive setup wizard to generate your `.env` configuration:*

```bash
python main.py --setup
```

### 3. Run the Bot

Launch the bot with your preferred browser and execution mode:

```bash
# Standard mode (sends heroes with stamina >= 60% to work every 30m)
python main.py

# Send all heroes to work regardless of stamina
python main.py --work-all

# Customize minimum stamina percentage threshold (e.g. 70%)
python main.py --min-stamina 70

# Select target browser (brave, chrome, firefox, edge, default)
python main.py --browser chrome

# Inner Bot Mode 1: Only refresh page when errors or disconnect popups occur
python main.py --only-refresh-on-error

# Inner Bot Mode 2: Periodically refresh browser every 30m to unstuck heroes
python main.py --refresh-interval 30

# Inner Bot Mode 3: Skip manual hero work clicks while monitoring errors
python main.py --skip-hero-work

# Dry Run Mode (simulates matching and actions without physical clicking)
python main.py --dry-run
```

---

## ⚙️ CLI Reference & Environment Variables

All settings can be specified via command-line arguments or saved in a `.env` file:

| CLI Argument | Environment Variable | Default | Description |
| :--- | :--- | :--- | :--- |
| `--check` | — | — | Runs system diagnostic test and exits |
| `--setup` | — | — | Runs interactive configuration setup wizard |
| `--browser` | `TARGET_BROWSER` | `brave` | Browser type (`brave`, `chrome`, `firefox`, `edge`, `default`) |
| `--browser-path` | `BROWSER_EXECUTABLE_PATH` | `""` | Custom absolute path to browser binary executable |
| `--monitor` | `SCREENSHOT_MONITOR_INDEX` | `1` | Screenshot monitor index (`1` = primary, `0` = all combined) |
| `--interval` | `HERO_WORK_INTERVAL_MINUTES` | `30` | Minutes between hero work cycles |
| `--work-all` | `HERO_WORK_MODE` | `stamina` | Send all heroes to work regardless of stamina |
| `--min-stamina` | `HERO_MIN_STAMINA` | `60` | Minimum stamina percentage threshold to send hero to work |
| `--only-refresh-on-error` | `ONLY_REFRESH_ON_ERROR` | `false` | Inner bot mode: only refresh page on game error |
| `--refresh-interval` | `REFRESH_INTERVAL_MINUTES` | `0.0` | Periodic page refresh interval in minutes |
| `--skip-hero-work` | `ENABLE_HERO_WORK_ACTIONS` | `true` | Skip manual hero menu work clicking |
| `--threshold` | `DEFAULT_MATCH_THRESHOLD` | `0.70` | Global visual pattern matching threshold |
| `--dry-run` | `DRY_RUN` | `false` | Dry run simulation without mouse clicks |
| `--headless` | `AUTO_LAUNCH_BROWSER` | `true` | Disable browser auto-launching |
| `--discord-webhook` | `DISCORD_WEBHOOK_URL` | `""` | Discord Webhook URL for alerts |
| `--telegram-token` | `TELEGRAM_BOT_TOKEN` | `""` | Telegram Bot API Token |
| `--telegram-chat-id` | `TELEGRAM_CHAT_ID` | `""` | Telegram Chat ID for alerts |

---

## 🔧 Platform-Specific Notes & Troubleshooting

### 🐧 Linux (Wayland vs X11)
- **Wayland (Ubuntu / GNOME / Sway / Hyprland)**:
  - **Sway / Hyprland / wlroots**: Uses `grim` for screen capture (`sudo apt install grim` or `sudo pacman -S grim`).
  - **Ubuntu GNOME (Mutter)**: GNOME's Mutter compositor does **not** support `grim`. If `grim` returns black or fails on Ubuntu GNOME:
    - **Recommended Solution**: Switch to **Ubuntu on Xorg**. Log out, click your username, click the gear icon (⚙️) in the bottom-right corner, select **"Ubuntu on Xorg"**, and log in.
    - **Alternative**: Install `gnome-screenshot` (`sudo apt install gnome-screenshot`).
- **Mouse Input Backends**: Supports PyAutoGUI, `/dev/uinput` kernel device, `ydotool`, `xdotool`, and Hyprland `hyprctl`.
- **Window Focusing**: To auto-focus the game browser tab before screenshots on X11, install `wmctrl` or `xdotool` (`sudo apt install wmctrl xdotool`). For Wayland users on Hyprland, `hyprctl` is used natively.

### 🪟 Windows
- PyAutoGUI standard mouse automation and MSS screen capture work out-of-the-box. Run terminal as Administrator if interacting with elevated browser windows.

### 🍎 macOS
- **Permissions**: Ensure your terminal (Terminal, iTerm2, or VS Code) has **Screen Recording** and **Accessibility** permissions granted in *System Preferences -> Privacy & Security*.

---

## 🧪 Testing

Run the automated test suite with pytest:

```bash
pytest
```

---

## ☕ Support the Project

If this bot saved you time or helped optimize your farming cycles, consider supporting development!

- **MetaMask / EVM (ETH, BSC, Polygon):** `0x87cAe5c5f4e8f3D5e9842b18c78e32a09b5C17Eb`
- **Bitcoin (BTC):** `bc1q8y736rfsyz5jp76gvdz9veddcktp00rjqaw69r`

---

## ⚠️ Disclaimer
This project is provided for educational and automation research purposes. Please ensure compliance with game terms of service.

