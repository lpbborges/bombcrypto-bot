# Bomb Crypto Automation Bot

A modular, computer-vision-powered Python bot for **Bomb Crypto** (https://game.bombcrypto.io/).

This bot uses OpenCV image pattern recognition (`cv2.matchTemplate`) and PyAutoGUI mouse simulation to automatically manage heroes, send them to work in Treasure Hunt, clear error modals, and re-connect when disconnected.

---

## Project Structure

```
bombcrypto-bot/
├── config.py             # Settings, thresholds, delays, timers & file paths
├── main.py               # Main bot loop entry point
├── requirements.txt      # Python package dependencies
├── README.md             # Setup and user guide
├── modules/
│   ├── __init__.py
│   ├── vision.py         # OpenCV template matching engine (mss + OpenCV)
│   ├── actions.py        # PyAutoGUI humanized mouse clicks & movements
│   └── bot_logic.py      # State machine & automation workflow
└── targets/              # Button template crop PNGs
    └── README.md         # Detailed instructions for image targets
```

---

## 🚀 Quick Start Guide

### 1. Install Dependencies

Ensure Python 3.8+ is installed on your system. Run:

```bash
cd bombcrypto-bot
pip install -r requirements.txt
```

### 2. Capture Target Button Images

Before running the bot, you must save small screenshot crops of the game buttons inside the `targets/` directory.

Refer to [`targets/README.md`](targets/README.md) for the complete list:
- `connect_wallet.png`
- `heroes_icon.png`
- `work_all_button.png`
- `close_button.png`
- `treasure_hunt_icon.png`
- `error_ok.png`

### 3. Run the Bot

Open https://game.bombcrypto.io/ in your web browser and execute:

```bash
python main.py
```

---

## ⚙️ Configuration Options (`config.py`)

You can tweak the following settings in `config.py`:

```python
# Confidence threshold for visual pattern matching (0.0 to 1.0)
DEFAULT_MATCH_THRESHOLD = 0.75

# How often to send heroes back to work (in minutes)
HERO_WORK_INTERVAL_MINUTES = 30

# Mouse interaction speed and humanized delays
MIN_CLICK_DURATION = 0.2
MAX_CLICK_DURATION = 0.5
MOUSE_CLICK_OFFSET = 5  # Pixels offset range from button center
```

---

## 🛡️ Anti-Stuck & Safety Features

- **PyAutoGUI Emergency Fail-Safe**: Move your mouse pointer to any of the 4 corners of your screen to immediately kill the bot execution.
- **Humanized Clicks**: Randomized click duration, Bezier mouse easing curves, and slight pixel position jitter.
- **Auto Error Recovery**: Detects "OK" error buttons and connection popups, automatically clearing them.

---

## ☕ Buy Me a Coffee

If this bot saved you time or helped optimize your farming cycles, consider supporting the project!

- **MetaMask / EVM (ETH, BSC, Polygon):** `0x87cAe5c5f4e8f3D5e9842b18c78e32a09b5C17Eb`
- **Bitcoin (BTC):** `bc1q8y736rfsyz5jp76gvdz9veddcktp00rjqaw69r`

---

## ⚠️ Disclaimer
This code is provided for educational and automation research purposes. Please ensure compliance with game terms of service.
