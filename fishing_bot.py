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

_local = threading.local()
def get_sct():
    if not hasattr(_local, "sct"):
        _local.sct = mss.MSS()
    return _local.sct

def close_sct():
    if hasattr(_local, "sct"):
        _local.sct.close()
        del _local.sct

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

def run_phase1(kb_ctrl, cfg, stop_event, log_cb=print) -> bool:
    """Single NET HAUL press. Returns True on success."""
    bar = dict(cfg["phase1_bar"])
    # Scan middle row of the bar
    scan = {**bar, "top": bar["top"] + bar["height"] // 2, "height": 1}
    lead = int(cfg["lead_fraction"] * bar["width"])
    deadline = time.time() + cfg["phase_timeout"]

    log_cb("  [P1] Watching pointer…")
    while not stop_event.is_set() and time.time() < deadline:
        row = capture(scan)
        ptr, gl, gr = find_pointer_and_green(row, cfg)

        if ptr != -1 and gl != -1:
            if (gl - lead) <= ptr <= (gr + lead):
                log_cb(f"    ✓ SPACE! ptr={ptr} green={gl}–{gr}")
                kb_ctrl.press(Key.space)
                time.sleep(0.05)
                kb_ctrl.release(Key.space)
                time.sleep(0.5)   # debounce
                return True

        time.sleep(cfg["poll_ms"] / 1000)

    log_cb("  [P1] Timeout.")
    return False

# ── Phase 2 — HAUL THE NET ───────────────────────────────────────────────────

def read_strain(cfg) -> str:
    """
    Finds the white pointer in the LINE STRAIN bar.
    Returns 'danger' (too far right), 'safe' (far left), or 'mid' (in between).
    """
    arr = capture(cfg["phase2_bar"])
    mid = arr[arr.shape[0] // 2]

    ptr_x = -1
    width = mid.shape[0]

    # Scan left → right to find the white pointer
    for x in range(width):
        r = int(mid[x, 0])
        g = int(mid[x, 1])
        b = int(mid[x, 2])
        if is_white(r, g, b, cfg):
            ptr_x = x
            break

    if ptr_x == -1:
        return "empty"

    pct = ptr_x / width
    if pct > 0.60:
        return "danger"
    elif pct < 0.15:
        return "safe"
    else:
        return "mid"

def read_progress(cfg) -> int:
    """Return 0–100 based on how much of the progress bar is filled (blue)."""
    arr = capture(cfg["phase2_progress"])
    mid = arr[arr.shape[0] // 2]
    r = mid[:, 0].astype(int)
    g = mid[:, 1].astype(int)
    b = mid[:, 2].astype(int)
    # Use strict brightness check so the dark grey empty bar isn't counted as filled
    filled = int(((b > 150) & (b > r) & (b > g) & (g > 80) & (r > 30)).sum())
    return int(filled / mid.shape[0] * 100)

def run_phase2(kb_ctrl, cfg, stop_event, log_cb=print) -> bool:
    """Haul the net: Hold 1s (or until danger), Sleep 2s, repeat 8 times."""
    log_cb("  [P2] Hauling (1s hold / 2s sleep, with danger check)…")
    
    for i in range(11):
        if stop_event.is_set():
            break
            
        log_cb(f"\r    Hold & Release {i+1}/8  ", end="")
        
        # Hold space for up to 1 second
        kb_ctrl.press(Key.space)
        hold_end = time.time() + 1.0
        while time.time() < hold_end and not stop_event.is_set():
            if read_strain(cfg) == "danger":
                break
            time.sleep(0.05)
        kb_ctrl.release(Key.space)
        
        if stop_event.is_set():
            break
            
        # Sleep for 2 seconds
        rest_end = time.time() + 2.0
        while time.time() < rest_end and not stop_event.is_set():
            time.sleep(0.1)

    log_cb("\n  [P2] ✓ Done")
    return True

# ── Main bot loop ─────────────────────────────────────────────────────────────

class FishingBot:
    def __init__(self, cfg, log_callback=None):
        self.cfg = cfg
        self.running = False
        self.stop_event = threading.Event()
        self.kb = KeyboardController()
        self._thread = None
        self.log_callback = log_callback

    def log(self, text, end="\n"):
        if self.log_callback:
            self.log_callback(text, end)
        else:
            print(text, end=end, flush=True)

    def start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.log("\n[BOT] ▶ Started — F11 to stop\n")

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        try:
            self.kb.release(Key.space)
        except Exception:
            pass
        self.log("\n[BOT] ■ Stopped.")

    def _loop(self):
        try:
            self._run_loop()
        except mss.exception.ScreenShotError:
            self.log("\n[ERR] Screen capture failed! Make sure FiveM is in 'Borderless' or 'Windowed' mode, NOT Exclusive Fullscreen!\n")
            self.stop()
        finally:
            close_sct()

    def _run_loop(self):
        cycle = 0
        while not self.stop_event.is_set():
            cycle += 1
            self.log(f"\n[BOT] ══ Cycle #{cycle} ══")

            # Cast net
            self.log("[BOT] Pressing E to cast…")
            self.kb.press("e")
            time.sleep(self.cfg["cast_hold"])
            self.kb.release("e")
            time.sleep(self.cfg["post_cast_wait"])
            if self.stop_event.is_set():
                break

            # Phase 1 × 3
            self.log("[BOT] Waiting for NET HAUL…")
            p1_hits = 0
            p1_deadline = time.time() + self.cfg["phase_timeout"]

            while p1_hits < 3 and not self.stop_event.is_set():
                if time.time() > p1_deadline:
                    self.log("[BOT] Phase 1 timed out — recasting.")
                    break
                phase = detect_phase(self.cfg)
                if phase == "phase1":
                    ok = run_phase1(self.kb, self.cfg, self.stop_event, log_cb=self.log)
                    if ok:
                        p1_hits += 1
                        self.log(f"[BOT] NET HAUL {p1_hits}/3 ✓")
                        p1_deadline = time.time() + self.cfg["phase_timeout"]
                        time.sleep(0.2)
                time.sleep(self.cfg["poll_ms"] / 1000)

            if self.stop_event.is_set():
                break
            if p1_hits < 3:
                self.log("[BOT] Phase 1 incomplete — recasting.")
                continue

            # Phase 2
            self.log("[BOT] Waiting for HAUL THE NET…")
            p2_deadline = time.time() + self.cfg["phase_timeout"]
            while not self.stop_event.is_set() and time.time() < p2_deadline:
                if detect_phase(self.cfg) == "phase2":
                    break
                time.sleep(self.cfg["poll_ms"] / 1000)
            else:
                self.log("[BOT] Phase 2 not found — recasting.")
                continue

            run_phase2(self.kb, self.cfg, self.stop_event, log_cb=self.log)
            self.log("[BOT] Resting 1s before next cast…")
            time.sleep(1.0)

        self.log("[BOT] Loop exited.")

    def listen_hotkeys(self):
        self.log("\n[HOT] F5=Start  F11=Stop  F12=Exit\n")
        def on_press(key):
            if key == Key.f5:
                self.start()
            elif key == Key.f11:
                self.stop()
            elif key == Key.f12:
                self.stop()
                self.log("[EXIT] Bye!")
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
