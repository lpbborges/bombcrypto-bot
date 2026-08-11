# Target Images Setup Guide

Save your small screen crops (PNG format) inside this `targets/` folder according to your exact game flow:

## Required Target Files

| Filename | Description / What to Crop |
| :--- | :--- |
| `confirm_profile_ok.png` | Crop of the **"OK"** profile confirmation button (appears first). |
| `connect_wallet.png` | Crop of the **"Connect Wallet"** button on the game login screen. |
| `select_metamask.png` | Crop of the **MetaMask** wallet option icon/button. |
| `metamask_sign.png` | Crop of the blue **"Sign"** button in the MetaMask extension popup window. |
| `bottom_arrow.png` | Crop of the **Arrow Icon at the bottom of the screen** that expands the HUD menu. |
| `heroes_button.png` | Crop of the **Heroes Icon** inside the opened bottom HUD menu. |
| `work_all_button.png` | Crop of the green **"Work All"** button inside the Heroes list modal. |
| `close_button.png` | Crop of the red **"X" / Close** button on top of the Heroes modal window. |
| `error_ok.png` / `error_ok_button.png` | Crop of the **"OK"** button on error or disconnection dialog popups. |
| `unknown_error.png` / `error_message.png` | Crop of the error message box or title text on connection error popups. |

## Execution Workflow

1. Start on direct URL: `https://game.bombcrypto.io/web/v13d/index.html?landing=treasure`
2. Click **Confirm Profile "OK"** button (`confirm_profile_ok.png`).
3. Click **Connect Wallet** (`connect_wallet.png`) -> Sign MetaMask (`metamask_sign.png` if required).
4. Wait for Treasure Hunt map to load.
5. Click **Bottom Arrow** (`bottom_arrow.png`) to open HUD menu.
6. Click **Heroes Button** (`heroes_button.png`) inside HUD menu.
7. Click **Work All** (`work_all_button.png`) -> Click **Close** (`close_button.png`).
