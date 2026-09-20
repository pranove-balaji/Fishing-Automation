"""
FiveM Fishing Bot — Vision-Based Auto Fishing
==============================================
Calibrated for 2560x1600 resolution from real screenshots.

Phase 1 — NET HAUL (x3):
  Finds the white moving pointer on the segmented bar.
  Presses SPACE the moment the pointer enters the dark-green zone.

Phase 2 — HAUL THE NET:
  Reads the LINE STRAIN rainbow bar.
  Holds SPACE while strain is green/yellow; releases when orange/red.
  Repeats until progress bar hits 100%.

Controls:
  F5  → Start bot
  F11 → Stop bot
  F12 → Exit
"""

import time, json, os, sys, threading
import numpy as np
import mss
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyboardController

CONFIG_FILE = "config.json"

# ── Colour helpers ───────────────────────────────────────────────────────────

def is_phase1_green(r, g, b, cfg):
    """Muted dark green used in NET HAUL bar: e.g. rgb(46,130,89)"""
    return (g > cfg["green_min"]
            and g > r * cfg["green_ratio"]
            and g > b * 1.2)

def is_white(r, g, b, cfg):
    """Bright white pointer: rgb(255,255,255)"""
    return r > cfg["white_min"] and g > cfg["white_min"] and b > cfg["white_min"]

def is_strain_safe(r, g, b, cfg):
    """Bright green in LINE STRAIN bar: rgb(43,212,122)"""
    return (g > cfg["strain_green_min"]
            and g > r * cfg["strain_green_ratio"])

def is_strain_danger(r, g, b, cfg):
    """Orange or red in LINE STRAIN bar."""
    return r > cfg["orange_r_min"] and g < cfg["orange_g_max"]

def is_cyan_icon(r, g, b):
    """Cyan headphone icon next to NET HAUL title: rgb(33,189,208)"""
    return b > 150 and g > 150 and r < 120

def is_blue_progress(r, g, b):
    """Blue progress bar fill in HAUL THE NET: rgb(47,155,255)"""
    return b > 150 and r > 30 and g > 80 and b > r and b > g

# ── Screen capture ───────────────────────────────────────────────────────────

_sct = None
def get_sct():
    global _sct
    if _sct is None:
        _sct = mss.mss()
    return _sct

def capture(region: dict) -> np.ndarray:
    """Returns HxWx3 RGB array."""
    sct = get_sct()
    img = sct.grab(region)
    arr = np.frombuffer(img.raw, dtype=np.uint8).reshape((img.height, img.width, 4))
    return arr[:, :, :3][:, :, ::-1]  # BGRA → RGB

# ── Phase detection ──────────────────────────────────────────────────────────

def detect_phase(cfg) -> str:
    """
    'phase1' — NET HAUL cyan icon visible at detect_phase1 region
    'phase2' — HAUL THE NET blue progress bar visible at detect_phase2 region
    'none'   — neither found
    """
    # Phase 1: small patch next to "NET HAUL" title has cyan icon pixel
    p1 = capture(cfg["detect_phase1"])
    r1, g1, b1 = p1[:,:,0].astype(int), p1[:,:,1].astype(int), p1[:,:,2].astype(int)
    cyan_count = int(((b1 > 150) & (g1 > 150) & (r1 < 120)).sum())
    if cyan_count > 5:
        return "phase1"

    # Phase 2: thin progress bar row has bright blue pixels
    p2 = capture(cfg["detect_phase2"])
    r2, g2, b2 = p2[:,:,0].astype(int), p2[:,:,1].astype(int), p2[:,:,2].astype(int)
    blue_count = int(((b2 > 150) & (b2 > r2) & (b2 > g2) & (g2 > 60)).sum())
    if blue_count > 20:
        return "phase2"

    return "none"

# ── Phase 1 — NET HAUL ───────────────────────────────────────────────────────

def find_pointer_and_green(row_rgb, cfg):
    """
    Scan a 1-pixel-tall row for white pointer and green zone.
    Returns (pointer_x, green_left, green_right) or (-1,-1,-1).
    """
    W = row_rgb.shape[1]
    ptr = -1
    g_left = -1
    g_right = -1
    white_run_start = -1

    for x in range(W):
        r = int(row_rgb[0, x, 0])
        g = int(row_rgb[0, x, 1])
        b = int(row_rgb[0, x, 2])

        if is_white(r, g, b, cfg):
            if white_run_start == -1:
                white_run_start = x
        else:
            if white_run_start != -1:
                ptr = (white_run_start + x) // 2
                white_run_start = -1

        if is_phase1_green(r, g, b, cfg):
            if g_left == -1:
                g_left = x
            g_right = x

    return ptr, g_left, g_right

def run_phase1(kb_ctrl, cfg, stop_event) -> bool:
    """Single NET HAUL press. Returns True on success."""
    bar = dict(cfg["phase1_bar"])
    # Scan middle row of the bar
    scan = {**bar, "top": bar["top"] + bar["height"] // 2, "height": 1}
    lead = int(cfg["lead_fraction"] * bar["width"])
    deadline = time.time() + cfg["phase_timeout"]

    print("  [P1] Watching pointer…")
    while not stop_event.is_set() and time.time() < deadline:
        row = capture(scan)
        ptr, gl, gr = find_pointer_and_green(row, cfg)

        if ptr != -1 and gl != -1:
            if (gl - lead) <= ptr <= (gr + lead):
                print(f"    ✓ SPACE! ptr={ptr} green={gl}–{gr}")
                kb_ctrl.press(Key.space)
                time.sleep(0.05)
                kb_ctrl.release(Key.space)
                time.sleep(0.5)   # debounce
                return True

        time.sleep(cfg["poll_ms"] / 1000)

    print("  [P1] Timeout.")
    return False

# ── Phase 2 — HAUL THE NET ───────────────────────────────────────────────────

def read_strain(cfg) -> str:
    """
    Sample the LINE STRAIN bar from right to left.
    Returns 'danger', 'safe', or 'empty'.
    """
    arr = capture(cfg["phase2_bar"])
    mid = arr[arr.shape[0] // 2]

    # Scan right → left to find the rightmost filled (non-dark) pixel
    for x in range(mid.shape[0] - 1, -1, -1):
        r = int(mid[x, 0])
        g = int(mid[x, 1])
        b = int(mid[x, 2])
        if r + g + b < 50:
            continue
        if is_strain_danger(r, g, b, cfg):
            return "danger"
        return "safe"
    return "empty"

def read_progress(cfg) -> int:
    """Return 0–100 based on how much of the progress bar is filled (blue)."""
    arr = capture(cfg["phase2_progress"])
    mid = arr[arr.shape[0] // 2]
    r = mid[:, 0].astype(int)
    g = mid[:, 1].astype(int)
    b = mid[:, 2].astype(int)
    filled = int(((b > 100) & (b > r) & (b > g) & (g > 40)).sum())
    return int(filled / mid.shape[0] * 100)

def run_phase2(kb_ctrl, cfg, stop_event) -> bool:
    """Haul the net until 100%. Returns True on completion."""
    print("  [P2] Hauling…")
    holding = False
    deadline = time.time() + cfg["phase_timeout"] * 4

    while not stop_event.is_set() and time.time() < deadline:
        progress = read_progress(cfg)
        strain   = read_strain(cfg)
        print(f"\r    progress={progress:3d}%  strain={strain:<7}", end="", flush=True)

        if progress >= 98:
            print(f"\n  [P2] ✓ Done at {progress}%")
            if holding:
                kb_ctrl.release(Key.space)
            return True

        if strain == "safe" and not holding:
            kb_ctrl.press(Key.space)
            holding = True
        elif strain == "danger" and holding:
            kb_ctrl.release(Key.space)
            holding = False
            time.sleep(cfg["haul_ease_delay"])

        time.sleep(cfg["poll_ms"] / 1000)

    if holding:
        kb_ctrl.release(Key.space)
    print("\n  [P2] Timeout.")
    return False

# ── Main bot loop ─────────────────────────────────────────────────────────────

class FishingBot:
    def __init__(self, cfg):
        self.cfg = cfg
        self.running = False
        self.stop_event = threading.Event()
        self.kb = KeyboardController()
        self._thread = None

    def start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("\n[BOT] ▶ Started — F11 to stop\n")

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        try:
            self.kb.release(Key.space)
        except Exception:
            pass
        print("\n[BOT] ■ Stopped.")

    def _loop(self):
        cycle = 0
        while not self.stop_event.is_set():
            cycle += 1
            print(f"\n[BOT] ══ Cycle #{cycle} ══")

            # Cast net
            print("[BOT] Pressing E to cast…")
            self.kb.press("e")
            time.sleep(self.cfg["cast_hold"])
            self.kb.release("e")
            time.sleep(self.cfg["post_cast_wait"])
            if self.stop_event.is_set():
                break

            # Phase 1 × 3
            print("[BOT] Waiting for NET HAUL…")
            p1_hits = 0
            p1_deadline = time.time() + self.cfg["phase_timeout"]

            while p1_hits < 3 and not self.stop_event.is_set():
                if time.time() > p1_deadline:
                    print("[BOT] Phase 1 timed out — recasting.")
                    break
                phase = detect_phase(self.cfg)
                if phase == "phase1":
                    ok = run_phase1(self.kb, self.cfg, self.stop_event)
                    if ok:
                        p1_hits += 1
                        print(f"[BOT] NET HAUL {p1_hits}/3 ✓")
                        p1_deadline = time.time() + self.cfg["phase_timeout"]
                        time.sleep(0.2)
                time.sleep(self.cfg["poll_ms"] / 1000)

            if self.stop_event.is_set():
                break
            if p1_hits < 3:
                print("[BOT] Phase 1 incomplete — recasting.")
                continue

            # Phase 2
            print("[BOT] Waiting for HAUL THE NET…")
            p2_deadline = time.time() + self.cfg["phase_timeout"]
            while not self.stop_event.is_set() and time.time() < p2_deadline:
                if detect_phase(self.cfg) == "phase2":
                    break
                time.sleep(self.cfg["poll_ms"] / 1000)
            else:
                print("[BOT] Phase 2 not found — recasting.")
                continue

            run_phase2(self.kb, self.cfg, self.stop_event)
            print("[BOT] Resting 1s before next cast…")
            time.sleep(1.0)

        print("[BOT] Loop exited.")

    def listen_hotkeys(self):
        print("\n[HOT] F5=Start  F11=Stop  F12=Exit\n")
        def on_press(key):
            if key == Key.f5:
                self.start()
            elif key == Key.f11:
                self.stop()
            elif key == Key.f12:
                self.stop()
                print("[EXIT] Bye!")
                os._exit(0)
        with keyboard.Listener(on_press=on_press) as lst:
            lst.join()

# ── Config ────────────────────────────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"[ERR] {CONFIG_FILE} not found! Download it alongside this script.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  FiveM Fishing Bot — Vision-Based")
    print("  Calibrated for 2560x1600")
    print("=" * 55)
    cfg = load_config()
    bot = FishingBot(cfg)
    bot.listen_hotkeys()
