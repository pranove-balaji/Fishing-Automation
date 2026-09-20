# 🎣 FiveM Auto Fishing Bot

An automated fishing bot for FiveM servers using real-time screen reading.
It watches your screen, detects the fishing minigame UI, and handles everything automatically.

> ⚠️ **Use responsibly.** Only use this on servers that allow automation/macros.
> Using it on servers that ban bots may result in your account being suspended.

---

## 📸 What It Automates

This bot handles the two-phase net fishing minigame:

### Phase 1 — NET HAUL (×3)
A white pointer moves across a segmented bar.
The bot watches in real time and presses `SPACE` the moment
the pointer enters the green zone — 3 times in a row.

```
[ ░░░░░ | ░░░░ |  ▌  | ████ | ░░░░ ]
                  ↑              ↑
               pointer       green zone  ← bot presses SPACE here
```

### Phase 2 — HAUL THE NET
A rainbow LINE STRAIN bar fills up as you reel in the net.
The bot holds `SPACE` to reel, and releases when the bar
turns orange/red to ease the tension — repeating until 100%.

```
[██████████████████████░░░░░░░░]  ← holding SPACE (green = safe)
[████████████████████████████▓▓]  ← releases SPACE (orange = danger)
```

---

## 💻 Requirements

| Requirement | Details |
|---|---|
| OS | Windows 10 / 11 |
| Python | 3.9 or higher |
| Screen Resolution | **2560×1600** (config is pre-calibrated for this) |
| FiveM window mode | Fullscreen or Borderless Windowed |

> If your resolution is different from 2560×1600, see the
> [Different Resolution](#-different-resolution) section below.

---

## 📁 Files

```
FishingBot/
├── fishing_bot.py     ← Main bot script
├── config.json        ← Screen region coordinates & colour thresholds
└── README.md          ← This file
```

Put all three files in the **same folder**.

---

## 🚀 Setup (First Time Only)

### Step 1 — Install Python

Download and install Python 3.11 from:
👉 https://www.python.org/downloads

> ✅ During installation, tick **"Add Python to PATH"** before clicking Install.
> Without this, the `python` command won't work.

---

### Step 2 — Download the Bot Files

Download these two files from wherever you got this README:
- `fishing_bot.py`
- `config.json`

Place them in a folder, for example: `C:\FishingBot\`

---

### Step 3 — Open Command Prompt as Administrator

1. Press the **Windows key**
2. Type `cmd`
3. **Right-click** on "Command Prompt"
4. Choose **"Run as Administrator"**

> ⚠️ Administrator mode is required so the bot can send
> keypresses to FiveM. Without it, the keys won't register in-game.

---

### Step 4 — Install Required Libraries

In the Command Prompt, paste this and press Enter:

```
pip install mss Pillow numpy pynput pyautogui
```

Wait for it to finish downloading. You only need to do this **once**.

---

### Step 5 — Navigate to Your Bot Folder

```
cd C:\FishingBot
```

Replace `C:\FishingBot` with wherever you actually saved the files.

---

### Step 6 — Run the Bot

```
python fishing_bot.py
```

You should see this:

```
=======================================================
  FiveM Fishing Bot — Vision-Based
  Calibrated for 2560x1600
=======================================================
[CFG] Loaded config.json
[HOT] F5=Start  F11=Stop  F12=Exit
```

---

## 🎮 How to Use

1. Open FiveM and join your server
2. Go to your **fishing spot** and get on your boat
3. Make sure you have **fishing bait** in your inventory
4. Switch to FiveM so it's your active window
5. Press **F5** — the bot starts automatically

The bot will:
- Press `E` to cast the net
- Watch for the NET HAUL bar and press `SPACE` on the green zone (×3)
- Hold/release `SPACE` during the HAUL THE NET strain bar
- Repeat the whole cycle forever until you stop it

---

## ⌨️ Controls

| Key | Action |
|-----|--------|
| `F5` | ▶ Start the bot |
| `F11` | ■ Stop the bot |
| `F12` | ✕ Exit the program |
| Mouse to **top-left corner** | 🚨 Emergency stop (instant abort) |

---

## 🖥️ Different Resolution?

The `config.json` that comes with this bot is pre-calibrated for **2560×1600**.

If you play at a different resolution (e.g. 1920×1080, 2560×1440), the bot will
scan the wrong part of the screen and won't work correctly.

### How to fix it:

1. **Take two screenshots** while fishing:
   - One when the **NET HAUL** bar appears
   - One when the **HAUL THE NET** / LINE STRAIN bar appears

2. **Share the screenshots** with whoever set this up for you (or open them in Paint)
   — the pixel coordinates of the bars can be read and a new `config.json` generated.

> Paint tip: hover over the edges of the UI bars and look at the pixel
> coordinates shown in the bottom status bar. Note the X and Y values
> for left edge, right edge, top, and bottom of each bar.

---

## ⚙️ config.json Explained

You generally don't need to edit this, but here's what each setting does:

```jsonc
{
  // Screen regions (left, top, width, height — all in pixels)
  "phase1_bar":      { ... },   // The NET HAUL segmented bar
  "phase2_bar":      { ... },   // The LINE STRAIN rainbow bar
  "phase2_progress": { ... },   // The thin progress bar showing 0–100%
  "detect_phase1":   { ... },   // Area checked to detect NET HAUL is active
  "detect_phase2":   { ... },   // Area checked to detect HAUL THE NET is active

  // Colour thresholds
  "green_min": 100,             // Min green brightness for NET HAUL green zone
  "green_ratio": 1.4,           // Green must be 1.4× brighter than red and blue
  "white_min": 180,             // Min brightness for the white pointer
  "strain_green_min": 180,      // Min green brightness for LINE STRAIN safe zone
  "strain_green_ratio": 2.5,    // LINE STRAIN green must be 2.5× brighter than red
  "orange_r_min": 240,          // Min red value to trigger danger (ease SPACE)
  "orange_g_max": 160,          // Max green value when in danger zone

  // Timing
  "lead_fraction": 0.01,        // Press SPACE slightly early (1% of bar width)
  "poll_ms": 8,                 // Screen scan every 8ms (~125 scans/sec)
  "haul_ease_delay": 0.10,      // Seconds to wait after releasing SPACE
  "cast_hold": 0.15,            // How long to hold E when casting
  "post_cast_wait": 1.5,        // Seconds to wait after casting before watching
  "phase_timeout": 25           // Seconds before giving up and recasting
}
```

---

## 🔧 Troubleshooting

| Problem | Fix |
|---|---|
| Bot presses SPACE too late / misses green | Increase `lead_fraction` in config.json (try `0.03`) |
| Bot doesn't detect green zone | Lower `green_min` in config.json (try `80`) |
| Bot holds SPACE too long and strain hits red | Lower `orange_g_max` (try `140`) or decrease `haul_ease_delay` |
| Keypresses don't register in FiveM | Run Command Prompt as **Administrator** |
| Bot prints "Phase not detected" repeatedly | Your resolution differs — see [Different Resolution](#-different-resolution) |
| Python not found | Reinstall Python and tick "Add Python to PATH" |
| `pip` not found | Close and reopen Command Prompt after installing Python |
| Bot starts but nothing happens | Make sure FiveM is the **active/focused window** when you press F5 |

---

## 📋 What the Console Output Means

While the bot runs, it prints live status in the Command Prompt:

```
[BOT] ══ Cycle #1 ══
[BOT] Pressing E to cast…
[BOT] Waiting for NET HAUL…
  [P1] Watching pointer…
    ✓ SPACE! ptr=312 green=324–453
[BOT] NET HAUL 1/3 ✓
    ✓ SPACE! ptr=318 green=324–453
[BOT] NET HAUL 2/3 ✓
    ✓ SPACE! ptr=330 green=324–453
[BOT] NET HAUL 3/3 ✓
[BOT] Waiting for HAUL THE NET…
  [P2] Hauling…
    progress= 17%  strain=safe
    progress= 39%  strain=safe
    progress= 68%  strain=danger
    progress= 71%  strain=safe
    progress=100%  strain=safe
  [P2] ✓ Done at 100%
[BOT] Resting 1s before next cast…
[BOT] ══ Cycle #2 ══
```

---

## ❓ FAQ

**Q: Will this get me banned?**
Depends entirely on the server. Many RP servers allow AFK farming scripts;
others have anti-cheat that detects automated input. Always check your server's rules first.

**Q: Does it work while I'm tabbed out?**
No. FiveM must be the active/focused window for keypresses to register.
You can minimise the Command Prompt but keep FiveM visible.

**Q: Can I change the key from SPACE to something else?**
Yes — open `fishing_bot.py` in Notepad, search for `Key.space` and replace it
with your desired key, e.g. `Key.enter` or `"e"`.

**Q: The bot keeps saying "Phase 1 incomplete — recasting." — what does that mean?**
The bot pressed E but didn't see the NET HAUL bar appear. Either the cast failed
(not enough bait, wrong position) or the screen regions are slightly off.
Try increasing `post_cast_wait` in config.json to give the game more time to load the UI.

**Q: How do I stop it instantly?**
Move your mouse to the **very top-left corner** of your screen — this triggers
PyAutoGUI's built-in failsafe and stops all input immediately.

---

## 🛠️ Built With

- [mss](https://python-mss.readthedocs.io/) — ultra-fast screen capture
- [Pillow](https://pillow.readthedocs.io/) — image processing
- [NumPy](https://numpy.org/) — fast pixel array operations
- [pynput](https://pynput.readthedocs.io/) — keyboard input simulation
- [PyAutoGUI](https://pyautogui.readthedocs.io/) — failsafe mouse abort

---

*Made for a FiveM net fishing minigame. Coordinates calibrated from real 2560×1600 gameplay screenshots.*
