import ctypes
import json
import keyboard
import os
import pyautogui
import pygetwindow as gw
import random
import struct
import threading
import time
import traceback
import tkinter as tk
import win32con
import win32gui
from ctypes import wintypes
from queue import Empty, Queue
from tkinter import ttk, messagebox

pyautogui.PAUSE = 0

# ==================== 全局变量 ====================
CONFIG_FILE = "config.json"
TIME_CONFIG_FILE = "time_config.json"
GAME_WINDOW_TITLE = "天龙八部"
SCREEN_CACHE_TTL = 0.03
HOME_TOGGLE_DEBOUNCE = 0.35
ERROR_LOG_COOLDOWN = 3.0
ATTACK_RECOVERY_RANGE = (0.035, 0.055)
BUFF_SKILL_SLEEP_RANGE = (0.09, 0.12)
TARGET_SWITCH_KEY = "F1"
TARGET_SWITCH_MIN_INTERVAL = 0.06
TARGET_SWITCH_REFRESH_TIMEOUT = 0.22
TARGET_SWITCH_POLL_INTERVAL = 0.018

running = True
paused = False
state_lock = threading.Lock()
ui_action_queue = Queue()
screen_cache_lock = threading.Lock()
screen_cache_image = None
screen_cache_time = 0.0
keyboard_hook = None
last_home_toggle_time = 0.0
last_error_signature = None
last_error_log_time = 0.0
last_target_switch_time = 0.0
mouse_action_lock = threading.Lock()
last_mouse_action_time = 0.0
MIN_MOUSE_ACTION_GAP = 0.08
ui_closing = False
game_window_hwnd = None

# ==================== 拟人化延时函数 ====================
def human_sleep(min_sec, max_sec):
    """
    产生自然的随机延时（偏向较短等待，提升效率）。
    
    修改点：
    1. 使用更左偏的 Beta 分布（均值约 0.15），大部分等待靠近 min_sec。
    2. 降低“走神加长”的概率至 1.2%，且加长幅度缩小。
    3. 提升“快速响应”概率至 3.5%，更快执行下一步。
    4. 保留最小延时保护。
    """
    # 区间极小时，直接均匀随机（几乎无开销）
    if max_sec - min_sec < 0.05:
        time.sleep(random.uniform(min_sec, max_sec))
        return

    # Beta(1.5, 8) 均值 ≈ 0.158，更加偏向区间左侧（短等待）
    t = random.betavariate(1.5, 8)
    delay = min_sec + (max_sec - min_sec) * t

    # 随机扰动（概率和幅度均做了效率优化）
    if random.random() < 0.012:          # 1.2% 概率：轻微“走神”
        delay += random.uniform(0.02, 0.06)
    elif random.random() < 0.035:        # 3.5% 概率：反应更快
        delay *= random.uniform(0.65, 0.92)

    # 保证最短延时至少 0.01 秒
    time.sleep(max(0.01, delay))

# ==================== 配置数据类 ====================
class ConfigData:
    def __init__(self):
        self.death_return_min = 20
        self.death_return_max = 25
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(TIME_CONFIG_FILE):
                with open(TIME_CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if not isinstance(config, dict):
                        raise ValueError("配置格式必须为对象")
                    self.death_return_min = config.get("death_return_min", 20)
                    self.death_return_max = config.get("death_return_max", 25)
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.death_return_min = 20
            self.death_return_max = 25

    def save_config(self):
        try:
            config = {
                "death_return_min": self.death_return_min,
                "death_return_max": self.death_return_max
            }
            with open(TIME_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置失败: {e}")

config_data = ConfigData()

# ==================== GUI 界面 ====================
root = tk.Tk()
root.title("运行中")
root.geometry("390x490")
root.resizable(False, False)
root.configure(bg='#f8f9fa')

def fix_taskbar_style():
    try:
        hwnd = root.winfo_id()
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        ex_style = (ex_style & ~win32con.WS_EX_TOOLWINDOW) | win32con.WS_EX_APPWINDOW
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
        win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                              win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)
    except Exception as e:
        print(f"任务栏样式修正失败: {e}")

root.update()
fix_taskbar_style()
root.bind_all("<Control-Tab>", lambda event: "break")

COLORS = {
    'primary': '#ffffff', 'secondary': '#6c757d', 'accent': '#ffffff',
    'background': '#f8f9fa', 'surface': '#ffffff', 'text_primary': '#212529',
    'text_secondary': '#6c757d', 'success': '#ffffff', 'warning': '#ffc107',
    'danger': '#dc3545', 'notebook_bg': '#f8f9fa', 'tab_bg': '#e9ecef',
    'tab_active_bg': '#ffffff', 'checkbox_bg': '#ffffff'
}
style = ttk.Style()
style.theme_use('clam')
style.configure('.', background=COLORS['background'])
style.configure('TFrame', background=COLORS['background'])
style.configure('TNotebook', background=COLORS['notebook_bg'], borderwidth=0, tabmargins=[0,0,0,0])
style.configure('TNotebook.Tab', background=COLORS['tab_bg'], foreground=COLORS['text_primary'],
                padding=[12,4], focuscolor=COLORS['notebook_bg'], font=('微软雅黑',11,'bold'))
style.map('TNotebook.Tab', background=[('selected', COLORS['tab_active_bg']), ('active', COLORS['primary'])],
          expand=[('selected',[1,1,1,0])])
style.configure('Custom.TFrame', background=COLORS['surface'])
style.configure('TLabelframe', background=COLORS['background'], relief='flat', borderwidth=0)
style.configure('TLabelframe.Label', background=COLORS['background'], foreground=COLORS['primary'],
                font=('微软雅黑',12,'bold'))
style.configure('Custom.TButton', background=COLORS['primary'], foreground='#000000',
                font=('微软雅黑',11,'bold'), focuscolor='none', padding=(10,5))
style.map('Custom.TButton', background=[('active',COLORS['secondary']), ('pressed',COLORS['accent'])])
style.configure('Status.TLabel', background=COLORS['surface'], foreground=COLORS['text_primary'],
                font=('微软雅黑',10), relief='sunken', padding=5)

main_frame = ttk.Frame(root, style='Custom.TFrame')
main_frame.pack(fill='both', expand=True, padx=0, pady=0)

notebook = ttk.Notebook(main_frame)
notebook.pack(fill='both', expand=True, padx=8, pady=8)

# ---------- 功能设置页 ----------
function_tab = ttk.Frame(notebook, style='Custom.TFrame')
notebook.add(function_tab, text="功能设置")

function_frame = ttk.LabelFrame(function_tab, text="请选择需要开启的功能", style='Custom.TFrame')
function_frame.pack(fill='x', pady=(0,12), padx=8)

checkbutton_vars = {
    "内挂挂机": tk.IntVar(),
    "死亡回点": tk.IntVar(),
    "打死怪": tk.IntVar(),
    "加状态": tk.IntVar(),
    "升级": tk.IntVar(),
    "组队": tk.IntVar(),
    "打绿怪": tk.IntVar(),
    "打BOSS": tk.IntVar(),

}
selected_options = {name: 0 for name in checkbutton_vars}

def update_selected_options(*_):
    with state_lock:
        for name, var in checkbutton_vars.items():
            selected_options[name] = var.get()

def get_selected_option(name):
    with state_lock:
        return selected_options.get(name, 0)

for var in checkbutton_vars.values():
    var.trace_add("write", update_selected_options)

checkbox_frame = ttk.Frame(function_frame, style='Custom.TFrame')
checkbox_frame.pack(fill='x', padx=8, pady=8)

col1_frame = ttk.Frame(checkbox_frame, style='Custom.TFrame')
col1_frame.pack(side='left', fill='x', expand=True, padx=(0,8))
col2_frame = ttk.Frame(checkbox_frame, style='Custom.TFrame')
col2_frame.pack(side='right', fill='x', expand=True, padx=(8,0))

functions = list(checkbutton_vars.keys())
mid_point = len(functions) // 2
for i, text in enumerate(functions):
    parent = col1_frame if i < mid_point else col2_frame
    cb = tk.Checkbutton(parent, text=text, variable=checkbutton_vars[text],
                        bg=COLORS['checkbox_bg'], fg='#000000', selectcolor=COLORS['primary'],
                        activebackground=COLORS['checkbox_bg'], activeforeground='#000000',
                        font=('微软雅黑',12), anchor='w', relief='solid', borderwidth=0)
    cb.pack(fill='x', pady=4)

button_frame = ttk.Frame(function_tab, style='Custom.TFrame')
button_frame.pack(fill='x', pady=(0,12), padx=8)

def save_settings():
    save_checkbutton_states()
    messagebox.showinfo("保存成功", "设置已成功保存！")

save_button = ttk.Button(button_frame, text="保存设置", command=save_settings, style='Custom.TButton')
save_button.pack(side='left', padx=(0,8))

pause_button = ttk.Button(button_frame, text="暂停/继续", command=lambda: toggle_pause(), style='Custom.TButton')
pause_button.pack(side='left', padx=8)

status_frame = ttk.LabelFrame(function_tab, text="系统状态", style='Custom.TFrame')
status_frame.pack(fill='x', pady=(0,12), padx=8)
status_label = ttk.Label(status_frame, text="正常运行", style='Status.TLabel')
status_label.pack(fill='x', padx=8, pady=8)

# ---------- 使用说明页 ----------
help_tab = ttk.Frame(notebook, style='Custom.TFrame')
notebook.add(help_tab, text="使用说明")
help_content = """
• F1: 切怪
• F2: 平推
• F3-F5: 技能
• F6: 加血
• F7/F8: 加蓝
• F9/F10: 珍兽加血
• Alt+9: 彻地符箓（位置10）
• Home键: 暂停/继续脚本
• 电脑分辨率(1366x768)
• 游戏默认取消经典视野。
• 游戏窗口分辨率(800x600)
• 软件以管理员权限运行。
• 单选内挂：内挂 · 抢怪 · 断线重连。
• 单选BOSS：死亡回苏州 ·BOSS · 马贼 · 活动本拉怪。
"""
help_frame = ttk.LabelFrame(help_tab, text="功能键说明", style='Custom.TFrame')
help_frame.pack(fill='both', expand=True, padx=8, pady=8)

help_text_frame = ttk.Frame(help_frame, style='Custom.TFrame')
help_text_frame.pack(fill='both', expand=True, padx=8, pady=8)

scrollbar = ttk.Scrollbar(help_text_frame)
scrollbar.pack(side='right', fill='y')

help_text = tk.Text(help_text_frame, height=14, wrap='word', bg=COLORS['surface'],
                    fg=COLORS['text_primary'], font=('微软雅黑',11),
                    yscrollcommand=scrollbar.set, padx=10, pady=10, relief='flat', borderwidth=0)
help_text.pack(side='left', fill='both', expand=True)
scrollbar.config(command=help_text.yview)
help_text.insert('1.0', help_content)
help_text.config(state='disabled')

# ---------- 回点时间页 ----------
time_tab = ttk.Frame(notebook, style='Custom.TFrame')
notebook.add(time_tab, text="回点时间")

death_time_frame = ttk.LabelFrame(time_tab, text="死亡回点时间设置", style='Custom.TFrame')
death_time_frame.pack(fill='x', pady=(10,5), padx=8)

min_frame = ttk.Frame(death_time_frame, style='Custom.TFrame')
min_frame.pack(fill='x', padx=10, pady=5)
ttk.Label(min_frame, text="最小等待时间(5秒):", style='Custom.TLabel').pack(side='left')
min_var = tk.StringVar(value=str(config_data.death_return_min))
min_spinbox = tk.Spinbox(min_frame, from_=5, to=1200, width=10, textvariable=min_var, font=('微软雅黑',10))
min_spinbox.pack(side='right', padx=5)

max_frame = ttk.Frame(death_time_frame, style='Custom.TFrame')
max_frame.pack(fill='x', padx=10, pady=5)
ttk.Label(max_frame, text="最大等待时间(20分钟):", style='Custom.TLabel').pack(side='left')
max_var = tk.StringVar(value=str(config_data.death_return_max))
max_spinbox = tk.Spinbox(max_frame, from_=6, to=1201, width=10, textvariable=max_var, font=('微软雅黑',10))
max_spinbox.pack(side='right', padx=5)

note_label = ttk.Label(death_time_frame,
                       text="设置死亡回点时的随机等待时间范围\n当前范围: {}-{}秒".format(
                           config_data.death_return_min, config_data.death_return_max),
                       style='Custom.TLabel', justify='center')
note_label.pack(pady=10)

def save_time_settings():
    try:
        min_val = int(min_var.get())
        max_val = int(max_var.get())
        if min_val < 1:
            messagebox.showerror("错误", "最小时间不能小于1秒！")
            return
        if max_val <= min_val:
            messagebox.showerror("错误", "最大时间必须大于最小时间！")
            return
        config_data.death_return_min = min_val
        config_data.death_return_max = max_val
        config_data.save_config()
        note_label.config(text="设置死亡回点时的随机等待时间范围\n当前范围: {}-{}秒".format(min_val, max_val))
        messagebox.showinfo("保存成功", "时间设置已保存！")
    except ValueError:
        messagebox.showerror("错误", "请输入有效的数字！")

save_time_button = ttk.Button(time_tab, text="保存时间设置", command=save_time_settings, style='Custom.TButton')
save_time_button.pack(pady=10)

def reset_time_settings():
    min_var.set("22")
    max_var.set("33")
    config_data.death_return_min = 22
    config_data.death_return_max = 33
    config_data.save_config()
    note_label.config(text="设置死亡回点时的随机等待时间范围\n当前范围: 22-33秒")
    messagebox.showinfo("重置成功", "已恢复默认时间设置！")

reset_button = ttk.Button(time_tab, text="恢复默认", command=reset_time_settings, style='Custom.TButton')
reset_button.pack(pady=5)

# ==================== 游戏核心函数 ====================
def activate_window():
    """查找、激活并最大化游戏窗口"""
    try:
        windows = gw.getAllTitles()
        target = [t for t in windows if GAME_WINDOW_TITLE in t]
        if not target:
            return False
        win = gw.getWindowsWithTitle(target[0])[0]
        win.activate()
        human_sleep(0.11, 0.13)
        hwnd = win._hWnd
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        human_sleep(0.11, 0.13)
        return True
    except Exception as e:
        print(f"激活窗口失败: {e}")
        return False

def periodic_window_check():
    return

def ensure_game_window_active():
    global game_window_hwnd
    try:
        foreground_hwnd = win32gui.GetForegroundWindow()
        if game_window_hwnd and foreground_hwnd == game_window_hwnd:
            return True
        foreground_title = win32gui.GetWindowText(foreground_hwnd)
        if GAME_WINDOW_TITLE in foreground_title:
            game_window_hwnd = foreground_hwnd
            return True
    except Exception:
        pass
    return False

def send_key_press(key):
    """发送按键，支持组合键"""
    if not ensure_game_window_active():
        return False
    if '+' in key:
        keys = key.split('+')
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(key)
    invalidate_screen_cache()
    return True

def send_key_press_fast(key):
    """战斗热路径按键：前台已是游戏时跳过慢窗口激活。"""
    global game_window_hwnd
    try:
        foreground_hwnd = win32gui.GetForegroundWindow()
        if game_window_hwnd and foreground_hwnd == game_window_hwnd:
            pass
        else:
            foreground_title = win32gui.GetWindowText(foreground_hwnd)
            if GAME_WINDOW_TITLE in foreground_title:
                game_window_hwnd = foreground_hwnd
            else:
                return False
    except Exception:
        return False
    if '+' in key:
        pyautogui.hotkey(*key.split('+'))
    else:
        pyautogui.press(key)
    invalidate_screen_cache()
    return True

def invalidate_screen_cache():
    global screen_cache_image, screen_cache_time
    with screen_cache_lock:
        screen_cache_image = None
        screen_cache_time = 0.0

def get_cached_screenshot(force_refresh=False):
    global screen_cache_image, screen_cache_time
    now = time.perf_counter()
    with screen_cache_lock:
        if (
            force_refresh
            or screen_cache_image is None
            or now - screen_cache_time > SCREEN_CACHE_TTL
        ):
            screen_cache_image = pyautogui.screenshot()
            screen_cache_time = now
        return screen_cache_image

def get_pixel_colors(x, y):
    screenshot = get_cached_screenshot()
    return screenshot.getpixel((x, y))

def get_pixels_snapshot():
    return get_cached_screenshot().load()

def get_colors_from_snapshot(*points):
    pixels = get_pixels_snapshot()
    return tuple(get_pixel_color_from_snapshot(pixels, x, y) for x, y in points)

def get_pixel_color_from_snapshot(pixels, x, y):
    return pixels[x, y]

def move_at_position(x, y):
    pyautogui.moveTo(int(x), int(y), duration=0)
    invalidate_screen_cache()

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

def click_at_position(screen_x, screen_y):
    global last_mouse_action_time
    with mouse_action_lock:
        now = time.monotonic()
        gap = MIN_MOUSE_ACTION_GAP - (now - last_mouse_action_time)
        if gap > 0:
            time.sleep(gap)
        pyautogui.moveTo(int(screen_x), int(screen_y), duration=0)
        pyautogui.mouseDown(button="left")
        human_sleep(0.011, 0.013)
        pyautogui.mouseUp(button="left")
        last_mouse_action_time = time.monotonic()
    invalidate_screen_cache()

def right_at_position(screen_x, screen_y):
    global last_mouse_action_time
    with mouse_action_lock:
        now = time.monotonic()
        gap = MIN_MOUSE_ACTION_GAP - (now - last_mouse_action_time)
        if gap > 0:
            time.sleep(gap)
        pyautogui.moveTo(int(screen_x), int(screen_y), duration=0)
        pyautogui.mouseDown(button="right")
        human_sleep(0.011, 0.013)
        pyautogui.mouseUp(button="right")
        last_mouse_action_time = time.monotonic()
    invalidate_screen_cache()

# ========== 像素相似判断 ==========
def colors_are_similar(c1, c2, tolerance=30):
    return all(abs(a-b) <= tolerance for a,b in zip(c1,c2))

PRIMARY_TARGET_POINTS = (
    (608, 86),
    (608, 103),
    (609, 123),
    (609, 142),
    (609, 162),
)
SECONDARY_TARGET_POINTS = (
    (711, 92),
    (711, 108),
    (711, 126),
    (711, 144),
    (711, 162),
)
BOSS_GUAI_LIST = [
    (438, 45, (252, 254, 159)),
    (452, 60, (252, 252, 255)),
    (440, 76, (255, 251, 243)),
    (438, 76, (132, 135, 116)),
]
TARGET_ACTIVE_COLOR = (255, 162, 150)
WHITE_TARGET_BLOCK_COLOR = (155, 153, 152)
RED_TARGET_COLOR = (155, 1, 1)
COMMON_SKILL_COLOR = (123, 101, 70)
ALT_SKILL_COLOR = (134, 117, 83)
def all_points_match(points, color):
    pixels = get_pixels_snapshot()
    return all(get_pixel_color_from_snapshot(pixels, x, y) == color for x, y in points)

def get_target_signature():
    pixels = get_pixels_snapshot()
    signature_points = (
        (278, 52),
        (279, 45),
        (278, 58),
        (405, 52),
        (437, 65),
        (465, 59),
    )
    return tuple(get_pixel_color_from_snapshot(pixels, x, y) for x, y in signature_points)

def wait_for_target_refresh(previous_signature=None, success_condition=None,
                            timeout=TARGET_SWITCH_REFRESH_TIMEOUT,
                            poll_interval=TARGET_SWITCH_POLL_INTERVAL):
    deadline = time.perf_counter() + timeout
    while True:
        invalidate_screen_cache()
        if success_condition and success_condition():
            return True
        if previous_signature is not None and get_target_signature() != previous_signature:
            return True
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return False
        time.sleep(min(poll_interval, remaining))

def switch_target(success_condition=None, timeout=TARGET_SWITCH_REFRESH_TIMEOUT):
    global last_target_switch_time
    elapsed = time.monotonic() - last_target_switch_time
    if elapsed < TARGET_SWITCH_MIN_INTERVAL:
        time.sleep(TARGET_SWITCH_MIN_INTERVAL - elapsed)

    previous_signature = get_target_signature()
    if not send_key_press_fast(TARGET_SWITCH_KEY):
        return False

    last_target_switch_time = time.monotonic()
    return wait_for_target_refresh(previous_signature, success_condition, timeout)

def handle_primary_target_switch():
    if all_points_match(PRIMARY_TARGET_POINTS, (1, 1, 1)):
        switch_target()

def handle_secondary_target_switch():
    if all_points_match(SECONDARY_TARGET_POINTS, (1, 1, 1)):
        if wait_for_target_refresh(
            previous_signature=get_target_signature(),
            timeout=0.12,
            poll_interval=TARGET_SWITCH_POLL_INTERVAL
        ):
            return
        if all_points_match(SECONDARY_TARGET_POINTS, (1, 1, 1)):
            switch_target()

def should_log_error(signature):
    global last_error_signature, last_error_log_time
    now = time.monotonic()
    if signature != last_error_signature or now - last_error_log_time >= ERROR_LOG_COOLDOWN:
        last_error_signature = signature
        last_error_log_time = now
        return True
    return False

def log_runtime_error(context, error):
    signature = (context, type(error).__name__, str(error))
    if should_log_error(signature):
        print(f"{context}: {error}")
        traceback.print_exc()

def target_state_matches(target_state_color, require_red_target):
    if require_red_target:
        return target_state_color == RED_TARGET_COLOR
    return target_state_color != WHITE_TARGET_BLOCK_COLOR

def wait_for_attack_condition(attack_condition, timeout=0.09, poll_interval=0.018):
    """切怪后短轮询目标状态：目标一刷新出来就立刻继续。"""
    deadline = time.perf_counter() + timeout
    while True:
        invalidate_screen_cache()
        if attack_condition():
            return True
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return False
        time.sleep(min(poll_interval, remaining))

def wait_for_target_active(timeout=0.09, poll_interval=0.018):
    return wait_for_attack_condition(
        lambda: get_pixel_colors(278, 52) == TARGET_ACTIVE_COLOR,
        timeout,
        poll_interval
    )

def run_skill_check(slot_x, slot_y, slot_color, hotkey, require_red_target):
    pixels = get_pixels_snapshot()
    current_slot_color = get_pixel_color_from_snapshot(pixels, slot_x, slot_y)
    target_active_color = get_pixel_color_from_snapshot(pixels, 278, 52)
    target_state_color = get_pixel_color_from_snapshot(pixels, 279, 45)
    if (
        colors_are_similar(slot_color, current_slot_color, 30)
        and target_active_color == TARGET_ACTIVE_COLOR
        and target_state_matches(target_state_color, require_red_target)
    ):
        send_key_press(hotkey)
        human_sleep(*ATTACK_RECOVERY_RANGE)

def run_skill_checks(skill_checks, require_red_target):
    for slot_x, slot_y, slot_color, hotkey in skill_checks:
        run_skill_check(slot_x, slot_y, slot_color, hotkey, require_red_target)

def execute_melee_battle(
    pre_attack_action,
    attack_condition,
    loop_count=9,
    reconfirm_after_switch=False,
):
    BB_zhuang_tai1()
    handle_primary_target_switch()
    handle_secondary_target_switch()
    pre_attack_action()
    for _ in range(loop_count):
        if attack_condition():
            send_key_press_fast('F2')
            human_sleep(*ATTACK_RECOVERY_RANGE)
        else:
            # BOSS 切怪后不能直接相信切怪函数返回值，必须重新读取
            # 当前目标状态；只有新目标再次满足条件才允许按 F2。
            switch_target(
                success_condition=None if reconfirm_after_switch else attack_condition,
                timeout=0.12,
            )
            if attack_condition():
                send_key_press_fast('F2')
                human_sleep(*ATTACK_RECOVERY_RANGE)
    BB_zhuang_tai2()

def is_white_melee_target():
    pixels = get_pixels_snapshot()
    c1 = get_pixel_color_from_snapshot(pixels, 278, 52)
    c2 = get_pixel_color_from_snapshot(pixels, 279, 45)
    return (
        (c1 == TARGET_ACTIVE_COLOR and c2 == RED_TARGET_COLOR)
        or (c1 == TARGET_ACTIVE_COLOR and c2 == (2, 153, 1))
    )

def is_boss_target():
    pixels = get_pixels_snapshot()
    bc3 = get_pixel_color_from_snapshot(pixels, 278, 52)
    bc4 = get_pixel_color_from_snapshot(pixels, 279, 45)
    bc5 = get_pixel_color_from_snapshot(pixels, 278, 58)
    bc6 = get_pixel_color_from_snapshot(pixels, 437, 65)
    bc7 = bc4
    bc8 = get_pixel_color_from_snapshot(pixels, 465, 59)
    return (
        (bc3 == TARGET_ACTIVE_COLOR and bc4 == RED_TARGET_COLOR)
        or (
            bc5 == TARGET_ACTIVE_COLOR
            and bc6 != (255, 253, 254)
            and bc7 != WHITE_TARGET_BLOCK_COLOR
            and bc8 != (143, 57, 0)
        )
    )

def is_mazei_target():
    pixels = get_pixels_snapshot()
    bc3 = get_pixel_color_from_snapshot(pixels, 278, 52)
    bc4 = get_pixel_color_from_snapshot(pixels, 453, 58)
    bc7 = get_pixel_color_from_snapshot(pixels, 279, 45)
    return (
        bc3 == TARGET_ACTIVE_COLOR
        and bc4 == (205, 195, 196)
        and bc7 != WHITE_TARGET_BLOCK_COLOR
    )

WHITE_SKILL_GROUP_1 = (
    (591, 672, COMMON_SKILL_COLOR, 'F3'),
    (627, 672, COMMON_SKILL_COLOR, 'F4'),
    (663, 672, COMMON_SKILL_COLOR, 'F5'),
)
RED_SKILL_GROUP_1 = (
    (591, 672, COMMON_SKILL_COLOR, 'F3'),
    (627, 672, COMMON_SKILL_COLOR, 'F4'),
    (663, 672, COMMON_SKILL_COLOR, 'F5'),
)

# ========== 基础功能函数（已全局降低延时）==========

def fang_ji_neng_bai():
    """白怪技能释放（已降低延时）"""
    run_skill_checks(WHITE_SKILL_GROUP_1, require_red_target=False)

def fang_ji_neng_hong():
    """红怪技能释放（已降低延时）"""
    run_skill_checks(RED_SKILL_GROUP_1, require_red_target=True)

# ========== 优化后的主要战斗函数 ==========

def da_lv_guai():
    """快速拉怪"""
    BB_zhuang_tai2()
    fang_ji_neng_bai()
    for _ in range(10):
        if wait_for_target_active(timeout=0.02, poll_interval=0.01):
            send_key_press_fast('F2')
            human_sleep(*ATTACK_RECOVERY_RANGE)
        switch_target()

def da_si_guai():
    """近战打白怪（优化版）"""
    execute_melee_battle(fang_ji_neng_bai, is_white_melee_target)
    
def da_boss():
    """BOSS打法（优化版）"""
    execute_melee_battle(
        fang_ji_neng_hong,
        is_boss_target,
        reconfirm_after_switch=True,
    )

def da_mazei():
    """马贼打法（优化版）"""
    execute_melee_battle(fang_ji_neng_hong, is_mazei_target)

# ---------- 辅助功能 ----------
def BB_zhuang_tai1():
    v5, v6 = get_colors_from_snapshot((95, 100), (200, 100))
    if v5==(16,4,0) and v6!=(255,162,150):
        send_key_press('F10')
        human_sleep(*BUFF_SKILL_SLEEP_RANGE)

def BB_zhuang_tai2():
    c5, c6 = get_colors_from_snapshot((95, 100), (210, 100))
    if c5==(16,4,0) and c6!=(255,162,150):
        send_key_press('F9')
        human_sleep(*BUFF_SKILL_SLEEP_RANGE)

def jia_zhuang_tai():
    z1, c1, c2 = get_colors_from_snapshot((278, 52), (64, 56), (130, 57))
    if c1==(8,0,0) and z1==(255,162,150) and c2!=(255,162,150):
        send_key_press('F6')
        human_sleep(0.11, 0.13)
        
    zz21, zc3, zc4 = get_colors_from_snapshot((278, 52), (64, 56), (120, 63))
    if zc3==(8,0,0) and zz21==(255,162,150) and zc4!=(193,188,255):
        send_key_press('F7')
        human_sleep(0.11, 0.13)
    BB_zhuang_tai1()
    z21, c3, c4 = get_colors_from_snapshot((278, 52), (64, 56), (130, 63))
    if c3==(8,0,0) and z21==(255,162,150) and c4!=(193,188,255):
        send_key_press('F8')
        human_sleep(0.11, 0.13)
    qz2, qc3, qc4, qc5, qc6 = get_colors_from_snapshot(
        (278, 52),
        (64, 56),
        (130, 63),
        (773, 686),
        (877, 640),
    )
    if qc3==(8,0,0) and qz2==(255,162,150) and qc5==(148,142,123) and qc6==(1,249,254)  and qc4!=(193,188,255):
        human_sleep(0.11, 0.13)
        click_at_position(880,641)
        human_sleep(0.11, 0.13)
        move_at_position(683,400)
        human_sleep(0.11, 0.13)
    BB_zhuang_tai2()

def nei_gua():
    color31 = get_pixel_colors(1343,139)
    if color31 == (255,211,49):
        human_sleep(0.11, 0.13)
        click_at_position(1343,139)
        human_sleep(0.11, 0.13)
        move_at_position(683,400)
        human_sleep(3, 4)

def duan_xian_chong_lian():
    color34, color35 = get_colors_from_snapshot((698, 188), (579, 205))
    if color34==(255,242,99) and color35==(255,242,99):
        human_sleep(23, 28)
        click_at_position(747,224)
        human_sleep(8, 9)
        activate_window()
        human_sleep(2.3, 2.4)

def si_wang_hui_dian():
    duan_xian_chong_lian()
    c32 = get_pixel_colors(555,262)
    c33 = get_pixel_colors(605,263)
    if c32==(37,37,37) and c33==(37,37,37):
        human_sleep(config_data.death_return_min, config_data.death_return_max)
        click_at_position(760,263)
        human_sleep(0.13, 0.16)
        click_at_position(760,263)
        human_sleep(7, 8)
        send_key_press('tab')
        human_sleep(0.23, 0.26)
        click_at_position(1248,325)
        human_sleep(0.13, 0.16)
        click_at_position(1248,325)
        human_sleep(1.2, 1.3)
        click_at_position(1339,492)
        human_sleep(4, 5)
        send_key_press('tab')
        human_sleep(1.2, 1.3)
        click_at_position(72,244)
        human_sleep(0.13, 0.16)
        click_at_position(72,244)
        human_sleep(7, 8)
        click_at_position(811,644)
        human_sleep(1.4, 1.6)
        click_at_position(767,529)
        human_sleep(1.4, 1.6)
        click_at_position(823,600)
        human_sleep(1.4, 1.6)
        click_at_position(697,489)
        human_sleep(7, 8)

    df32 = get_pixel_colors(1239,47)
    df33 = get_pixel_colors(1248,44)
    df34 = get_pixel_colors(1260,44)
    df35 = get_pixel_colors(1272,48)
    if df32==(243,215,2) and df33==(255,245,0) and df34==(232,218,3) and df35==(237,201,2):
        human_sleep(1.2, 1.3)
        send_key_press('tab')
        human_sleep(0.23, 0.26)
        click_at_position(1248,325)
        human_sleep(0.13, 0.16)
        click_at_position(1248,325)
        human_sleep(1.2, 1.3)
        click_at_position(1339,492)
        human_sleep(4, 5)
        send_key_press('tab')
        human_sleep(1.2, 1.3)
        click_at_position(72,244)
        human_sleep(0.13, 0.16)
        click_at_position(72,244)
        human_sleep(7, 8)
        click_at_position(811,644)
        human_sleep(1.4, 1.6)
        click_at_position(767,529)
        human_sleep(1.4, 1.6)
        click_at_position(823,600)
        human_sleep(1.4, 1.6)
        click_at_position(697,489)
        human_sleep(7, 8)

    dl32 = get_pixel_colors(1239,45)
    dl33 = get_pixel_colors(1249,43)
    dl34 = get_pixel_colors(1262,44)
    dl35 = get_pixel_colors(1271,44)
    if dl32==(253,232,0) and dl33==(245,236,1) and dl34==(255,240,0) and dl35==(255,240,0):
        click_at_position(811,644)
        human_sleep(1.4, 1.6)
        click_at_position(767,529)
        human_sleep(1.4, 1.6)
        click_at_position(823,600)
        human_sleep(1.4, 1.6)
        click_at_position(697,489)
        human_sleep(7, 8)

def si_wang_su_zhou():
    duan_xian_chong_lian()
    c32 = get_pixel_colors(555,262)
    c33 = get_pixel_colors(605,263)
    if c32==(37,37,37) and c33==(37,37,37):
        human_sleep(10, 15)
        click_at_position(10,14)
        human_sleep(0.13, 0.16)
        click_at_position(760,263)
        human_sleep(7, 8)
        send_key_press('tab')
        human_sleep(0.23, 0.26)
        click_at_position(1248,325)
        human_sleep(0.13, 0.16)
        click_at_position(1248,325)
        human_sleep(1.2, 1.3)
        click_at_position(1339,492)
        human_sleep(4, 5)
        send_key_press('tab')
        human_sleep(1.2, 1.3)
        click_at_position(72,244)
        human_sleep(0.13, 0.16)
        click_at_position(72,244)
        human_sleep(7, 8)

    df32 = get_pixel_colors(1239,47)
    df33 = get_pixel_colors(1248,44)
    df34 = get_pixel_colors(1260,44)
    df35 = get_pixel_colors(1272,48)
    if df32==(243,215,2) and df33==(255,245,0) and df34==(232,218,3) and df35==(237,201,2):
        human_sleep(1.2, 1.3)
        send_key_press('tab')
        human_sleep(0.23, 0.26)
        click_at_position(1248,325)
        human_sleep(0.13, 0.16)
        click_at_position(1248,325)
        human_sleep(1.2, 1.3)
        click_at_position(1339,492)
        human_sleep(4, 5)
        send_key_press('tab')
        human_sleep(1.2, 1.3)
        click_at_position(72,244)
        human_sleep(0.13, 0.16)
        click_at_position(72,244)
        human_sleep(7, 8)


def zu_dui():
    c126, c127 = get_colors_from_snapshot((998, 710), (1063, 187))
    if c126==(61,54,32) and c127!=(248,196,88):
        human_sleep(1.2, 1.3)
        click_at_position(998,710)
        human_sleep(1.2, 1.3)
        move_at_position(963,453)
        human_sleep(1.2, 1.3)

    for _ in range(7):
        c124, c125 = get_colors_from_snapshot((1063, 187), (970, 498))
        if c124==(248,196,88) and c125==(253,235,120):
            human_sleep(1.2, 1.3)
            click_at_position(970,498)
            human_sleep(1.2, 1.3)
            move_at_position(963,453)
            human_sleep(1.2, 1.3)

    c128, c129 = get_colors_from_snapshot((1063, 187), (970, 498))
    if c128==(248,196,88) and c129!=(253,235,120):
        human_sleep(1.2, 1.3)
        send_key_press('esc')
        human_sleep(1.2, 1.3)

    dz6, dz7 = get_colors_from_snapshot((59, 69), (3, 163))
    if dz6==(209,31,10) and dz7==(0,0,0):
        human_sleep(2.2, 2.3)
        right_at_position(26,167)
        human_sleep(1.2, 1.3)
        click_at_position(44,241)
        human_sleep(1.2, 1.3)
        move_at_position(963,453)
        human_sleep(1.2, 1.3)

    dz6, dz7 = get_colors_from_snapshot((59, 69), (3, 163))
    if dz6==(209,31,10) and dz7!=(0,0,0):
        human_sleep(2.2, 2.3)
        right_at_position(37,59)
        human_sleep(1.2, 1.3)
        click_at_position(68,70)
        human_sleep(1.2, 1.3)
        move_at_position(963,453)
        human_sleep(1.2, 1.3)

def sheng_ji():
    sc1 = get_pixel_colors(863,667)
    if sc1==(155,152,255) or sc1==(186,41,225):
        human_sleep(1.2, 1.3)
        click_at_position(304,709)
        human_sleep(1.2, 1.3)
        click_at_position(549,474)
        human_sleep(1.2, 1.3)
        send_key_press('esc')
        human_sleep(1.2, 1.3)
    sc2 = get_pixel_colors(155,434)
    if sc2==(219,248,119):
        human_sleep(1.2, 1.3)
        send_key_press('esc')
        human_sleep(1.2, 1.3)

def zhen_shou_chu_zhan():
    c22, c23, ccc23 = get_colors_from_snapshot((64, 56), (95, 100), (279, 45))
    if c22==(8,0,0)  and  c23!=(16,4,0) and ccc23!=(155,1,1) :
        human_sleep(1.2, 1.3)
        click_at_position(372,711)
        human_sleep(1.2, 1.3)

    c25 = get_pixel_colors(520,504)
    cc25 = get_pixel_colors(95, 100) 
    if c25==(255,255,251) and  cc25 !=(16,4,0)  :
        human_sleep(1.2, 1.3)
        click_at_position(196,452)
        human_sleep(1.2, 1.3)
        click_at_position(255,423)
        human_sleep(1.2, 1.3)
        click_at_position(195,492)
        human_sleep(3.1, 3.3)

    dc25 = get_pixel_colors(520,504)
    if dc25==(255,255,251)  :
        human_sleep(1.2, 1.3)
        send_key_press('esc')
        human_sleep(1.2, 1.3)

def run_selected_options():
    while is_running():
        if not is_paused():
            try:
                if get_selected_option("内挂挂机"):
                    nei_gua()
                    zhen_shou_chu_zhan()
                if get_selected_option("死亡回点"):
                    si_wang_hui_dian()
                if get_selected_option("打死怪"):
                    da_si_guai()
                if get_selected_option("加状态"):
                    jia_zhuang_tai()
                if get_selected_option("升级"):
                    sheng_ji()
                if get_selected_option("组队"):
                    zu_dui()
                if get_selected_option("打绿怪"):
                    da_lv_guai()
                if get_selected_option("打BOSS"):
                    da_boss()
                    zhen_shou_chu_zhan()
                    si_wang_su_zhou()
                    if get_pixel_colors(453,58) == (205,195,196):
                        da_mazei()
                    for x, y, col in BOSS_GUAI_LIST:
                        if get_pixel_colors(x, y) == col:
                            da_lv_guai()
            except Exception as e:
                log_runtime_error("执行异常", e)
        human_sleep(0.08, 0.12)

# ==================== 控制函数 ====================
def set_paused(value):
    global paused
    with state_lock:
        paused = value

def is_paused():
    with state_lock:
        return paused

def is_running():
    with state_lock:
        return running

def enqueue_ui_update(paused_state):
    if not ui_closing:
        ui_action_queue.put(("pause_state", paused_state))

def apply_pause_state(paused_state):
    if ui_closing:
        return
    status_text = "已暂停" if paused_state else "运行中"
    button_text = "继续脚本" if paused_state else "暂停脚本"
    status_label.config(text=status_text)
    root.title(status_text)
    pause_button.config(text=button_text)
    root.update_idletasks()

def toggle_pause():
    new_state = not is_paused()
    set_paused(new_state)
    enqueue_ui_update(new_state)

def on_key_event(event):
    global last_home_toggle_time
    if event.name == "home" and event.event_type == "down":
        now = time.monotonic()
        if now - last_home_toggle_time < HOME_TOGGLE_DEBOUNCE:
            return
        last_home_toggle_time = now
        toggle_pause()

def process_ui_queue():
    if ui_closing:
        return
    try:
        while True:
            action, value = ui_action_queue.get_nowait()
            if action == "pause_state":
                apply_pause_state(value)
    except Empty:
        pass
    try:
        root.after(50, process_ui_queue)
    except tk.TclError:
        pass

def load_checkbutton_states():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                states = json.load(f)
                if not isinstance(states, dict):
                    raise ValueError("配置格式必须为对象")
                for name, var in checkbutton_vars.items():
                    if name in states:
                        var.set(states[name])
            update_selected_options()
    except Exception as e:
        print(f"加载功能配置失败: {e}")
        for var in checkbutton_vars.values():
            var.set(0)
        update_selected_options()

def save_checkbutton_states():
    try:
        states = {name: var.get() for name, var in checkbutton_vars.items()}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(states, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存功能配置失败: {e}")

def shutdown():
    global running, keyboard_hook, ui_closing
    with state_lock:
        running = False
    ui_closing = True
    if keyboard_hook is not None:
        try:
            keyboard.unhook(keyboard_hook)
        except Exception as e:
            print(f"注销热键失败: {e}")
        keyboard_hook = None
    invalidate_screen_cache()
    try:
        if root.winfo_exists():
            root.destroy()
    except tk.TclError:
        pass

def on_close():
    shutdown()

# ==================== 启动 ====================
activate_window()

thread = threading.Thread(target=run_selected_options, daemon=True)
thread.start()

load_checkbutton_states()
update_selected_options()
process_ui_queue()
root.protocol("WM_DELETE_WINDOW", on_close)
keyboard_hook = keyboard.on_press(on_key_event)

root.mainloop()
