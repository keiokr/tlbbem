# -*- coding: utf-8 -*-
"""EM helper - lightweight heal/status assistant.

\u79fb\u9664\u653b\u51fb/\u5207\u602a\u903b\u8f91\uff0c\u4f7f\u7528 Win32 \u539f\u751f\u952e\u9f20\u4e0e\u50cf\u7d20\u91c7\u6837\u3002
\u4fdd\u6301\u5341\u5b57 5 \u50cf\u7d20\u91c7\u6837\uff0c\u964d\u4f4e CPU \u4e0e\u5185\u5b58\u5360\u7528\u3002
"""

import ctypes
import os
import pyautogui
import sys
import threading
import time
import tkinter as tk
from collections import Counter
from ctypes import wintypes
from queue import Empty, Queue
from tkinter import messagebox, ttk

pyautogui.PAUSE = 0

# ------------------------- Win32 / process setup -------------------------

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

SW_MAXIMIZE = 3
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
KEYEVENTF_KEYUP = 0x0002
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000
VK_HOME = 0x24
HOTKEY_HOME_ID = 1001
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

ULONG_PTR_T = ctypes.c_ulong if ctypes.sizeof(ctypes.c_void_p) == 4 else ctypes.c_ulonglong


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR_T),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR_T),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", INPUTUNION)]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.GetPixel.restype = wintypes.DWORD
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

# ------------------------------ Configuration -----------------------------

GAME_WINDOW_TITLES = ("\u5929\u9f99\u516b\u90e8",)
HOME_TOGGLE_DEBOUNCE = 0.18

EXIST_COLOR_DEFAULT = (0, 0, 0)
BLOOD_COLOR = (255, 162, 150)
DEAD_COLOR = (255, 162, 150)
EXIST_USE_NOT_EQUAL = False
BLOOD_USE_NOT_EQUAL = True
DEAD_USE_NOT_EQUAL = True
CLICK_OFFSET = (20, 0)
MAX_TEAM_SIZE = 6
TEAM_SLOT_START = 0
COLOR_TOLERANCE = 10
EXACT_COLOR_TOLERANCE = 2

HEAL_KEY = "F3"
REVIVE_KEY = "F4"
HEAL_COOLDOWN = 1.5
HEAL_BUFFER = 0.2
CLICK_DELAY = 0.03
LOOP_INTERVAL = 0.05
IDLE_INTERVAL = 0.05
REVIVE_CAST_TIME = 5.0
HEAL_STATUSES = {"low", "mid", "high"}

# \u5341\u5b57\u91c7\u6837\uff1a\u4e2d\u5fc3\u70b9 + \u4e0a\u4e0b\u5de6\u53f3\uff0c\u5171 5 \u4e2a\u50cf\u7d20\u3002
POINT_SAMPLE_OFFSETS = ((0, 0),)
KEY_HOLD_SECONDS = 0.028

BB_EXIST_POS = (95, 100)
BB_EXIST_COLOR = (16, 4, 0)
BB_HP_CHECK_POS = (210, 100)
BB_MP_CHECK_POS = (200, 100)
BB_RECOVERY_CONFIRMATIONS = 2
BB_RECOVERY_COOLDOWN = 3.0
SELF_DEAD_POS = (558, 263)
SELF_DEAD_COLOR = (37, 37, 37)

TEAMMATES = [
    {"name": "\u961f\u53cb1", "exist_pos": (12, 52), "exist_color": (8, 0, 0), "dead_pos": (82, 57), "hp_points": {"low": (100, 57), "mid": (140, 57), "high": (180, 57)}},
    {"name": "\u961f\u53cb2", "exist_pos": (5, 167), "exist_color": (0, 0, 0), "dead_pos": (45, 151), "hp_points": {"low": (60, 151), "mid": (95, 151), "high": (130, 151)}},
    {"name": "\u961f\u53cb3", "exist_pos": (3, 210), "exist_color": (0, 0, 0), "dead_pos": (45, 196), "hp_points": {"low": (60, 196), "mid": (95, 196), "high": (130, 196)}},
    {"name": "\u961f\u53cb4", "exist_pos": (3, 256), "exist_color": (0, 0, 0), "dead_pos": (45, 241), "hp_points": {"low": (60, 241), "mid": (95, 241), "high": (130, 241)}},
    {"name": "\u961f\u53cb5", "exist_pos": (3, 298), "exist_color": (0, 0, 0), "dead_pos": (45, 286), "hp_points": {"low": (60, 286), "mid": (95, 286), "high": (130, 286)}},
    {"name": "\u961f\u53cb6", "exist_pos": (3, 346), "exist_color": (0, 0, 0), "dead_pos": (45, 331), "hp_points": {"low": (60, 331), "mid": (95, 331), "high": (130, 331)}},
]

# --------------------------------- State ----------------------------------

running = True
paused = False
f3_heal_enabled = True
f4_revive_enabled = True
state_enabled = True
ui_closing = False
game_window_hwnd = None
hotkey_thread_id = 0
last_hotkey_time = 0.0
last_heal_time = [0.0] * MAX_TEAM_SIZE
mouse_action_lock = threading.Lock()
last_mouse_action_time = 0.0
MIN_MOUSE_ACTION_GAP = 0.05
bb_hp_missing_hits = 0
bb_mp_missing_hits = 0
last_bb_hp_recovery_time = 0.0
last_bb_mp_recovery_time = 0.0
state_lock = threading.Lock()
ui_action_queue = Queue()


# ----------------------------- State helpers ------------------------------

def set_locked(name, value):
    globals()[name] = value


def set_paused(value):
    with state_lock:
        set_locked("paused", bool(value))


def is_paused():
    with state_lock:
        return paused


def is_running():
    with state_lock:
        return running


def should_stop_or_pause():
    return not is_running() or is_paused()


def set_f3_heal_enabled(value):
    with state_lock:
        set_locked("f3_heal_enabled", bool(value))


def set_f4_revive_enabled(value):
    with state_lock:
        set_locked("f4_revive_enabled", bool(value))


def set_state_enabled(value):
    with state_lock:
        set_locked("state_enabled", bool(value))


def is_f3_heal_enabled():
    with state_lock:
        return f3_heal_enabled


def is_f4_revive_enabled():
    with state_lock:
        return f4_revive_enabled


def is_state_enabled():
    with state_lock:
        return state_enabled


def get_heal_cooldown():
    with state_lock:
        return HEAL_COOLDOWN


def set_heal_cooldown(value):
    with state_lock:
        set_locked("HEAL_COOLDOWN", max(0.1, float(value)))


def interruptible_sleep(seconds, check_interval=0.05):
    end = time.monotonic() + max(0.0, seconds)
    while is_running():
        if is_paused():
            return False
        left = end - time.monotonic()
        if left <= 0:
            return True
        time.sleep(min(check_interval, left))
    return False


def steady_sleep(seconds):
    """Short action wait with pause/exit checks and no random jitter."""
    return interruptible_sleep(seconds, check_interval=min(0.03, max(0.005, seconds)))


def human_sleep(min_sec, max_sec):
    return steady_sleep((min_sec + max_sec) / 2.0)


# ----------------------------- Win32 helpers ------------------------------

def _window_text(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _is_game_title(title):
    return any(t and t in title for t in GAME_WINDOW_TITLES)


def activate_window():
    global game_window_hwnd
    try:
        hwnds = []

        @WNDENUMPROC
        def enum_proc(hwnd, _lparam):
            if user32.IsWindowVisible(hwnd) and _is_game_title(_window_text(hwnd)):
                hwnds.append(hwnd)
                return False
            return True

        user32.EnumWindows(enum_proc, 0)
        if not hwnds:
            return False
        game_window_hwnd = hwnds[0]
        user32.ShowWindow(game_window_hwnd, SW_MAXIMIZE)
        user32.SetForegroundWindow(game_window_hwnd)
        return True
    except Exception:
        return False


def foreground_is_game():
    global game_window_hwnd
    try:
        hwnd = user32.GetForegroundWindow()
        if game_window_hwnd and hwnd == game_window_hwnd:
            return True
        title = _window_text(hwnd)
        if _is_game_title(title):
            game_window_hwnd = hwnd
            return True
    except Exception:
        pass
    return False


def _vk_for_key(key):
    name = key.strip().upper()
    if name.startswith("F") and name[1:].isdigit():
        n = int(name[1:])
        if 1 <= n <= 24:
            return 0x70 + n - 1
    if name == "HOME":
        return VK_HOME
    if len(name) == 1:
        vk = user32.VkKeyScanW(ord(name)) & 0xFF
        if vk:
            return vk
    raise ValueError(f"Unsupported key: {key}")


def _send_keyboard_input(vk, flags=0):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0)
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1


def send_key_press_fast(key):
    if should_stop_or_pause() or not foreground_is_game():
        return False
    try:
        vk = _vk_for_key(key)
        ok1 = _send_keyboard_input(vk, 0)
        steady_sleep(KEY_HOLD_SECONDS)
        ok2 = _send_keyboard_input(vk, KEYEVENTF_KEYUP)
        return ok1 and ok2
    except Exception:
        return False


def send_key_press(key):
    return send_key_press_fast(key)


def _send_mouse_input(flags):
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0)
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1


def _absolute_mouse_xy(x, y):
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = max(1, user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    height = max(1, user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    ax = int(round((int(x) - left) * 65535 / max(1, width - 1)))
    ay = int(round((int(y) - top) * 65535 / max(1, height - 1)))
    return max(0, min(65535, ax)), max(0, min(65535, ay))


def _send_mouse_move_absolute(x, y):
    ax, ay = _absolute_mouse_xy(x, y)
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi = MOUSEINPUT(dx=ax, dy=ay, mouseData=0, dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, time=0, dwExtraInfo=0)
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1


def click_at_position(x, y):
    """左键点击：先移动到位，再按下、停顿、松开。"""
    if should_stop_or_pause():
        return False
    if not foreground_is_game():
        activate_window()
        steady_sleep(0.05)
        if should_stop_or_pause() or not foreground_is_game():
            return False

    x, y = int(x), int(y)
    global last_mouse_action_time
    with mouse_action_lock:
        now = time.monotonic()
        gap = MIN_MOUSE_ACTION_GAP - (now - last_mouse_action_time)
        if gap > 0:
            time.sleep(gap)
        pyautogui.moveTo(x, y, duration=0)
        pyautogui.mouseDown(button="left")
        steady_sleep(0.05)
        pyautogui.mouseUp(button="left")
        last_mouse_action_time = time.monotonic()
    return True


# ----------------------------- Pixel helpers ------------------------------

def _colorref_to_rgb(value):
    return (value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF)


def _pixel_from_dc(hdc, x, y):
    value = gdi32.GetPixel(hdc, int(x), int(y))
    if value == 0xFFFFFFFF:
        return (0, 0, 0)
    return _colorref_to_rgb(value)


def _stable_pixel_from_dc(hdc, x, y):
    colors = [_pixel_from_dc(hdc, x + dx, y + dy) for dx, dy in POINT_SAMPLE_OFFSETS]
    common, count = Counter(colors).most_common(1)[0]
    return common if count >= 3 else colors[0]


def get_pixel_colors(x, y):
    hdc = user32.GetDC(None)
    if not hdc:
        return (0, 0, 0)
    try:
        return _stable_pixel_from_dc(hdc, x, y)
    finally:
        user32.ReleaseDC(None, hdc)


def get_colors_from_snapshot(*points):
    hdc = user32.GetDC(None)
    if not hdc:
        return tuple((0, 0, 0) for _ in points)
    try:
        return tuple(_stable_pixel_from_dc(hdc, x, y) for x, y in points)
    finally:
        user32.ReleaseDC(None, hdc)


def all_points_match(points, color):
    return all(color_close(c, color, EXACT_COLOR_TOLERANCE) for c in get_colors_from_snapshot(*points))


def invalidate_screen_cache():
    # Compatibility shim: current version uses lightweight immediate GetPixel sampling.
    return None


def color_close(rgb, target, tolerance):
    return all(abs(a - b) <= tolerance for a, b in zip(rgb, target))


def color_match(rgb, target):
    return color_close(rgb, target, COLOR_TOLERANCE)


def point_met(point, color, not_equal=False):
    matched = color_match(get_pixel_colors(*point), color)
    return not matched if not_equal else matched


# ------------------------------ Heal logic --------------------------------

def mate_cfg(i):
    return TEAMMATES[i] if 0 <= i < min(MAX_TEAM_SIZE, len(TEAMMATES)) else None


def teammate_exists(i):
    cfg = mate_cfg(i)
    return bool(i >= TEAM_SLOT_START and cfg and point_met(cfg["exist_pos"], cfg.get("exist_color", EXIST_COLOR_DEFAULT), EXIST_USE_NOT_EQUAL))


def existing_team_slots():
    return [i for i in range(TEAM_SLOT_START, min(MAX_TEAM_SIZE, len(TEAMMATES))) if teammate_exists(i)]


def mate_dead(i):
    cfg = mate_cfg(i)
    return bool(cfg and point_met(cfg["dead_pos"], DEAD_COLOR, DEAD_USE_NOT_EQUAL))


def mate_status(i):
    cfg = mate_cfg(i)
    if not cfg:
        return None
    if mate_dead(i):
        return "dead"
    points = cfg["hp_points"]
    for status in ("low", "mid", "high"):
        if point_met(points[status], BLOOD_COLOR, BLOOD_USE_NOT_EQUAL):
            return status
    return "full"


def mate_click_pos(i):
    cfg = mate_cfg(i)
    return None if not cfg else (cfg["exist_pos"][0] + CLICK_OFFSET[0], cfg["exist_pos"][1] + CLICK_OFFSET[1])


def click_mate(i):
    pos = mate_click_pos(i)
    return bool(pos and click_at_position(*pos) and interruptible_sleep(CLICK_DELAY))


def is_mp_ready_for_heal():
    c1, c2, c3 = get_colors_from_snapshot((278, 52), (64, 56), (130, 63))
    return color_close(c3, (193, 188, 255), EXACT_COLOR_TOLERANCE) if color_close(c1, (8, 0, 0), EXACT_COLOR_TOLERANCE) and color_close(c2, BLOOD_COLOR, EXACT_COLOR_TOLERANCE) else False


def ensure_mp_before_heal():
    if is_mp_ready_for_heal():
        return True
    c4, c5 = get_colors_from_snapshot((278, 52), (110, 63))
    if not color_close(c4, BLOOD_COLOR, EXACT_COLOR_TOLERANCE) or color_close(c5, (193, 188, 255), EXACT_COLOR_TOLERANCE):
        return True
    send_key_press("F8")
    human_sleep(0.11, 0.13)
    return True


def extra_mp_check():
    c1, c2, c3 = get_colors_from_snapshot((278, 52), (64, 56), (120, 63))
    if color_close(c2, (8, 0, 0), EXACT_COLOR_TOLERANCE) and color_close(c1, BLOOD_COLOR, EXACT_COLOR_TOLERANCE) and not color_close(c3, (193, 188, 255), EXACT_COLOR_TOLERANCE):
        return send_key_press("F7") and interruptible_sleep(0.8)
    return True


def bb_bar_missing(check_pos):
    colors = get_colors_from_snapshot(BB_EXIST_POS, check_pos)
    if not color_close(colors[0], BB_EXIST_COLOR, COLOR_TOLERANCE):
        return False
    return not color_close(colors[1], BLOOD_COLOR, COLOR_TOLERANCE)


def is_self_dead():
    return color_close(
        get_pixel_colors(*SELF_DEAD_POS),
        SELF_DEAD_COLOR,
        EXACT_COLOR_TOLERANCE,
    )


def pet_exists():
    return color_close(
        get_pixel_colors(*BB_EXIST_POS),
        BB_EXIST_COLOR,
        COLOR_TOLERANCE,
    )


def ensure_pet_hp_before_heal():
    """F3/F6 加血前检查一次珍兽；不健康时只按一次 F10，然后继续。"""
    if should_stop_or_pause() or is_self_dead():
        return False
    if not pet_exists():
        return True
    if bb_bar_missing(BB_HP_CHECK_POS):
        send_key_press("F10")
        human_sleep(0.09, 0.12)
    return True


def maybe_press_bb_recovery(kind, key, check_pos):
    global bb_hp_missing_hits, bb_mp_missing_hits, last_bb_hp_recovery_time, last_bb_mp_recovery_time
    if should_stop_or_pause():
        return False
    missing = bb_bar_missing(check_pos)
    if kind == "hp":
        bb_hp_missing_hits = bb_hp_missing_hits + 1 if missing else 0
        hits = bb_hp_missing_hits
        last_time = last_bb_hp_recovery_time
    else:
        bb_mp_missing_hits = bb_mp_missing_hits + 1 if missing else 0
        hits = bb_mp_missing_hits
        last_time = last_bb_mp_recovery_time
    if not missing or hits < BB_RECOVERY_CONFIRMATIONS:
        return False
    now = time.monotonic()
    if now - last_time < BB_RECOVERY_COOLDOWN:
        return False
    steady_sleep(0.035)
    if should_stop_or_pause() or not bb_bar_missing(check_pos):
        if kind == "hp":
            bb_hp_missing_hits = 0
        else:
            bb_mp_missing_hits = 0
        return False
    success = send_key_press(key)
    if success:
        if kind == "hp":
            last_bb_hp_recovery_time = now
            bb_hp_missing_hits = 0
        else:
            last_bb_mp_recovery_time = now
            bb_mp_missing_hits = 0
        human_sleep(0.09, 0.12)
    return success


def bb_recovery():
    maybe_press_bb_recovery("hp", "F10", BB_HP_CHECK_POS)
    if should_stop_or_pause():
        return
    maybe_press_bb_recovery("mp", "F9", BB_MP_CHECK_POS)


def can_heal(i):
    return time.monotonic() - last_heal_time[i] >= get_heal_cooldown() + HEAL_BUFFER


def heal_mate(i):
    if should_stop_or_pause() or is_self_dead():
        return False
    if mate_status(i) not in HEAL_STATUSES or not ensure_mp_before_heal() or should_stop_or_pause():
        return False
    if (
        mate_status(i) not in HEAL_STATUSES
        or not click_mate(i)
        or should_stop_or_pause()
        or is_self_dead()
    ):
        return False
    if mate_status(i) not in HEAL_STATUSES:
        return False
    if not ensure_mp_before_heal() or should_stop_or_pause() or is_self_dead():
        return False
    success = send_key_press(HEAL_KEY)
    if success:
        last_heal_time[i] = time.monotonic()
    if not interruptible_sleep(get_heal_cooldown()):
        return False
    mate_status(i)
    return success


def team_statuses():
    return {i: mate_status(i) for i in existing_team_slots()}


def alive_teammates_all_full(statuses):
    alive_statuses = [status for status in statuses.values() if status != "dead"]
    return bool(alive_statuses) and all(status == "full" for status in alive_statuses)


def can_press_revive(statuses):
    return alive_teammates_all_full(statuses)


def revive_dead(statuses):
    for i, status in statuses.items():
        if status != "dead" or should_stop_or_pause():
            continue
        if not click_mate(i) or should_stop_or_pause():
            continue
        current_statuses = team_statuses()
        if not can_press_revive(current_statuses) or should_stop_or_pause():
            continue
        send_key_press(REVIVE_KEY)
        interruptible_sleep(REVIVE_CAST_TIME)
        return True
    return False


def self_recovery():
    c1, c2, c3 = get_colors_from_snapshot((278, 52), (64, 56), (130, 57))
    if color_close(c2, (8, 0, 0), EXACT_COLOR_TOLERANCE) and color_close(c1, BLOOD_COLOR, EXACT_COLOR_TOLERANCE) and not color_close(c3, BLOOD_COLOR, EXACT_COLOR_TOLERANCE):
        send_key_press("F6")
        human_sleep(0.11, 0.13)
    if should_stop_or_pause():
        return
    c4, c5 = get_colors_from_snapshot((278, 52), (110, 63))
    if color_close(c4, BLOOD_COLOR, EXACT_COLOR_TOLERANCE) and not color_close(c5, (193, 188, 255), EXACT_COLOR_TOLERANCE):
        send_key_press("F8")
        human_sleep(0.11, 0.13)


def heal_by_priority(statuses, target, healed):
    while not should_stop_or_pause() and not is_self_dead():
        candidates = [i for i, s in statuses.items() if s == target and i not in healed]
        if not candidates:
            return statuses
        i = candidates[0]
        if not can_heal(i):
            return statuses
        if heal_mate(i):
            healed.add(i)
        statuses = team_statuses()
    return statuses


def run_em_heal_once():
    if should_stop_or_pause():
        return
    pet_ready_for_heal = True
    if is_f3_heal_enabled() or is_state_enabled():
        pet_ready_for_heal = ensure_pet_hp_before_heal()
    if is_state_enabled():
        self_recovery()
        if should_stop_or_pause():
            return
        bb_recovery()
        if should_stop_or_pause():
            return
    statuses = team_statuses()
    if not statuses:
        return
    if is_f3_heal_enabled() and pet_ready_for_heal and not is_self_dead():
        healed = set()
        for level in ("low", "mid", "high"):
            statuses = heal_by_priority(statuses, level, healed)
    if not should_stop_or_pause() and is_state_enabled():
        extra_mp_check()
    if not should_stop_or_pause() and is_f4_revive_enabled():
        revive_dead(team_statuses())


def run_selected_options():
    while is_running():
        if is_paused():
            time.sleep(0.10)
            continue
        try:
            if is_f3_heal_enabled() or is_f4_revive_enabled() or is_state_enabled():
                run_em_heal_once()
                interruptible_sleep(LOOP_INTERVAL)
            else:
                interruptible_sleep(IDLE_INTERVAL)
        except Exception:
            interruptible_sleep(IDLE_INTERVAL)


# ------------------------------ Hotkeys/UI --------------------------------

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


SETTINGS_FILE = os.path.join(app_dir(), "coem.ini")
DEFAULT_OPTIONS = {"f3_heal": 0, "f4_revive": 0, "state": 0}


def load_option_settings():
    data = DEFAULT_OPTIONS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().lower()
                if key in data:
                    data[key] = 1 if value in ("1", "true", "yes", "on") else 0
    except OSError:
        pass
    return data


def save_option_settings(data):
    try:
        tmp = SETTINGS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for key in ("f3_heal", "f4_revive", "state"):
                f.write(f"{key}={1 if data.get(key) else 0}\n")
        os.replace(tmp, SETTINGS_FILE)
    except OSError:
        pass


def set_pause_from_ui(paused_state):
    set_paused(paused_state)
    if not ui_closing:
        ui_action_queue.put(("pause_state", paused_state))


def toggle_pause():
    set_pause_from_ui(not is_paused())


def hotkey_loop():
    global hotkey_thread_id, last_hotkey_time
    hotkey_thread_id = kernel32.GetCurrentThreadId()
    user32.RegisterHotKey(None, HOTKEY_HOME_ID, MOD_NOREPEAT, VK_HOME)
    msg = MSG()
    try:
        while is_running():
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_HOME_ID:
                now = time.monotonic()
                if now - last_hotkey_time >= HOME_TOGGLE_DEBOUNCE:
                    last_hotkey_time = now
                    ui_action_queue.put(("toggle_pause", None))
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        user32.UnregisterHotKey(None, HOTKEY_HOME_ID)


root = tk.Tk()
root.title("\u8fd0\u884c")
root.geometry("380x420+80+80")
root.resizable(False, False)
root.configure(bg="#f8f9fa")
try:
    ico = resource_path("coem.ico")
    if os.path.exists(ico):
        root.iconbitmap(ico)
except Exception:
    pass

style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background="#f8f9fa")
style.configure("TLabel", background="#f8f9fa", font=("Microsoft YaHei UI", 10))
style.configure("Title.TLabel", background="#f8f9fa", font=("Microsoft YaHei UI", 13, "bold"))
style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(8, 4))
style.configure("TLabelframe", background="#f8f9fa")
style.configure("TLabelframe.Label", background="#f8f9fa", font=("Microsoft YaHei UI", 10, "bold"))


top_frame = ttk.Frame(root)
top_frame.pack(fill="x", padx=12, pady=(10, 4))
status_label = ttk.Label(top_frame, text="\u8fd0\u884c", style="Title.TLabel")
status_label.pack(side="left")
pause_button = ttk.Button(top_frame, text="\u6682\u505c", command=toggle_pause, width=14)
pause_button.pack(side="right", padx=(8, 0))

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=12, pady=(6, 12))
function_tab = ttk.Frame(notebook)
help_tab = ttk.Frame(notebook)
notebook.add(function_tab, text="\u529f\u80fd")
notebook.add(help_tab, text="\u8bf4\u660e")
main_frame = ttk.Frame(function_tab)
main_frame.pack(fill="both", expand=True, padx=14, pady=12)

option_settings = load_option_settings()
f3_heal_var = tk.IntVar(value=option_settings["f3_heal"])
f4_revive_var = tk.IntVar(value=option_settings["f4_revive"])
state_var = tk.IntVar(value=option_settings["state"])
heal_cooldown_var = tk.StringVar(value=f"{get_heal_cooldown():.2f}".rstrip("0").rstrip("."))


def update_enabled_options(*_):
    f3_on = f3_heal_var.get() == 1
    f4_on = f4_revive_var.get() == 1
    state_on = state_var.get() == 1
    set_f3_heal_enabled(f3_on)
    set_f4_revive_enabled(f4_on)
    set_state_enabled(state_on)
    save_option_settings({"f3_heal": f3_on, "f4_revive": f4_on, "state": state_on})


def apply_heal_cooldown_from_gui():
    try:
        value = float(heal_cooldown_var.get().strip())
        if value <= 0:
            raise ValueError
        set_heal_cooldown(value)
        heal_cooldown_var.set(f"{get_heal_cooldown():.2f}".rstrip("0").rstrip("."))
    except ValueError:
        heal_cooldown_var.set(f"{get_heal_cooldown():.2f}".rstrip("0").rstrip("."))
        messagebox.showerror("\u53c2\u6570\u9519\u8bef", "F3 \u65f6\u95f4\u8bf7\u8f93\u5165\u5927\u4e8e 0 \u7684\u6570\u5b57\uff0c\u4f8b\u5982\uff1a1.5")


f3_heal_var.trace_add("write", update_enabled_options)
f4_revive_var.trace_add("write", update_enabled_options)
state_var.trace_add("write", update_enabled_options)

function_frame = ttk.LabelFrame(main_frame, text="\u529f\u80fd")
function_frame.pack(fill="x", pady=(0, 10))
cb_frame = ttk.Frame(function_frame)
cb_frame.pack(fill="x", padx=10, pady=8)
for index, (text, var) in enumerate((("F3 \u52a0\u8840", f3_heal_var), ("\u72b6\u6001 / \u56de\u84dd / BB", state_var), ("F4 \u6551\u4eba", f4_revive_var))):
    tk.Checkbutton(
        cb_frame,
        text=text,
        variable=var,
        bg="#f8f9fa",
        fg="#000000",
        selectcolor="#ffffff",
        activebackground="#f8f9fa",
        activeforeground="#000000",
        font=("Microsoft YaHei UI", 10),
        anchor="w",
    ).grid(row=index, column=0, sticky="w", padx=(0, 18), pady=6)

setting_frame = ttk.LabelFrame(main_frame, text="\u5ce8\u7709\u53c2\u6570")
setting_frame.pack(fill="x", pady=(0, 10))
f3_row = ttk.Frame(setting_frame)
f3_row.pack(fill="x", padx=12, pady=10)
ttk.Label(f3_row, text="F3 \u65f6\u95f4(\u79d2)\uff1a").grid(row=0, column=0, sticky="w")
f3_entry = ttk.Entry(f3_row, textvariable=heal_cooldown_var, width=8)
f3_entry.grid(row=0, column=1, sticky="w", padx=(8, 12))
f3_entry.bind("<Return>", lambda _: apply_heal_cooldown_from_gui())
ttk.Button(f3_row, text="\u5e94\u7528", command=apply_heal_cooldown_from_gui, width=10).grid(row=0, column=2, sticky="e")
f3_row.columnconfigure(1, weight=1)


def apply_pause_state(paused_state):
    if ui_closing:
        return
    text = "\u6682\u505c" if paused_state else "\u8fd0\u884c"
    status_label.config(text=text)
    root.title(text)
    pause_button.config(text="\u7ee7\u7eed" if paused_state else "\u6682\u505c")
    root.update_idletasks()


def process_ui_queue():
    if ui_closing:
        return
    try:
        while True:
            action, value = ui_action_queue.get_nowait()
            if action == "pause_state":
                apply_pause_state(value)
            elif action == "toggle_pause":
                toggle_pause()
    except Empty:
        pass
    try:
        root.after(80, process_ui_queue)
    except tk.TclError:
        pass


def shutdown():
    global running, ui_closing
    with state_lock:
        running = False
    ui_closing = True
    if hotkey_thread_id:
        try:
            user32.PostThreadMessageW(hotkey_thread_id, WM_QUIT, 0, 0)
        except Exception:
            pass
    try:
        if root.winfo_exists():
            root.destroy()
    except tk.TclError:
        pass


help_frame = ttk.LabelFrame(help_tab, text="\u8bf4\u660e")
help_frame.pack(fill="both", expand=True, padx=12, pady=12)
ttk.Label(
    help_frame,
    text="Home\uff1a\u542f\u52a8/\u6682\u505c\u3002\nF3\uff1a\u52a0\u8840\uff08\u6b7b\u4ea1\u4e0d\u52a0\uff09\u3002\nF4\uff1a\u6709\u6b7b\u961f\u53cb + \u6d3b\u961f\u53cb\u5168 full \u65f6\u6551\u4eba\u3002\n\u72b6\u6001\uff1a\u56de\u84dd\u3001BB \u6062\u590d\u3001\u84dd\u91cf\u68c0\u67e5\u3002",
    wraplength=300,
    justify="left",
    font=("Microsoft YaHei UI", 9),
).pack(fill="both", expand=True, padx=8, pady=6)

update_enabled_options()
threading.Thread(target=activate_window, daemon=True).start()
threading.Thread(target=run_selected_options, daemon=True).start()
threading.Thread(target=hotkey_loop, daemon=True).start()
process_ui_queue()
root.protocol("WM_DELETE_WINDOW", shutdown)
root.mainloop()
