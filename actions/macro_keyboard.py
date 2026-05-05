# actions/macro_keyboard.py
import ast
import json
import os
import time
from pathlib import Path

from evdev import ecodes as e

ACTION_INFO = {
    "id": "macro_keyboard",
    "name": "ระบบรันมาโครคีย์บอร์ด",
    "priority": 10,
    "is_blocking": False,
}

# 🗺️ คลังรหัสคีย์
K_MAP = {
    "a": e.KEY_A,
    "b": e.KEY_B,
    "c": e.KEY_C,
    "d": e.KEY_D,
    "e": e.KEY_E,
    "f": e.KEY_F,
    "g": e.KEY_G,
    "h": e.KEY_H,
    "i": e.KEY_I,
    "j": e.KEY_J,
    "k": e.KEY_K,
    "l": e.KEY_L,
    "m": e.KEY_M,
    "n": e.KEY_N,
    "o": e.KEY_O,
    "p": e.KEY_P,
    "q": e.KEY_Q,
    "r": e.KEY_R,
    "s": e.KEY_S,
    "t": e.KEY_T,
    "u": e.KEY_U,
    "v": e.KEY_V,
    "w": e.KEY_W,
    "x": e.KEY_X,
    "y": e.KEY_Y,
    "z": e.KEY_Z,
    "1": e.KEY_1,
    "2": e.KEY_2,
    "3": e.KEY_3,
    "4": e.KEY_4,
    "5": e.KEY_5,
    "6": e.KEY_6,
    "7": e.KEY_7,
    "8": e.KEY_8,
    "9": e.KEY_9,
    "0": e.KEY_0,
    "ctrl": e.KEY_LEFTCTRL,
    "lctrl": e.KEY_LEFTCTRL,
    "rctrl": e.KEY_RIGHTCTRL,
    "shift": e.KEY_LEFTSHIFT,
    "lshift": e.KEY_LEFTSHIFT,
    "rshift": e.KEY_RIGHTSHIFT,
    "alt": e.KEY_LEFTALT,
    "space": e.KEY_SPACE,
    "enter": e.KEY_ENTER,
    "backspace": e.KEY_BACKSPACE,
    "tab": e.KEY_TAB,
    "esc": e.KEY_ESC,
    "up": e.KEY_UP,
    "down": e.KEY_DOWN,
    "left": e.KEY_LEFT,
    "right": e.KEY_RIGHT,
    "f1": e.KEY_F1,
    "f2": e.KEY_F2,
    "f3": e.KEY_F3,
    "f4": e.KEY_F4,
    "f5": e.KEY_F5,
    "f6": e.KEY_F6,
    "f7": e.KEY_F7,
    "f8": e.KEY_F8,
    "f9": e.KEY_F9,
    "f10": e.KEY_F10,
    "f11": e.KEY_F11,
    "f12": e.KEY_F12,
}


def load_macro_library():
    path = Path(__file__).resolve().parent.parent / "config" / "macros.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def execute_step(ui, step):
    if isinstance(step, list):
        # Combo (เช่น กด Ctrl + C พร้อมกัน)
        codes = [K_MAP.get(k.lower()) for k in step if k.lower() in K_MAP]
        for c in codes:
            ui.write(e.EV_KEY, c, 1)
        ui.syn()
        time.sleep(0.05)
        for c in codes:
            ui.write(e.EV_KEY, c, 0)
        ui.syn()
    else:
        # ปุ่มเดี่ยว
        code = K_MAP.get(step.lower())
        if code:
            ui.write(e.EV_KEY, code, 1)
            ui.syn()
            time.sleep(0.03)
            ui.write(e.EV_KEY, code, 0)
            ui.syn()


def is_input_active(joystick, val):
    """ฟังก์ชันเช็คสถานะปุ่ม/แกน/D-Pad แบบรองรับการกด Combo ทุกรูปแบบ"""
    if val is None:
        return False
    try:
        if isinstance(val, int):
            return joystick.get_button(val)
        if isinstance(val, list):
            return all(is_input_active(joystick, i) for i in val)
        if isinstance(val, dict):
            if "hat" in val:
                return joystick.get_hat(val["hat"]) == tuple(val["dir"])
            if "axis" in val:
                v = joystick.get_axis(val["axis"])
                return v > 0.8 if val["val"] > 0 else v < -0.8
    except:
        pass
    return False


def _trigger_macro(ui_virtual, state_key, is_active, macro_name, macro_library):
    was_active = run._pressed_state.get(state_key, False)
    if is_active and not was_active:
        run._pressed_state[state_key] = True
        sequence = macro_library.get(macro_name)
        if sequence:
            # print(f"🚀 [Macro Engine] รันมาโคร: {macro_name}")
            for step in sequence:
                execute_step(ui_virtual, step)
                time.sleep(0.01)
    elif not is_active:
        run._pressed_state[state_key] = False


def run(ui_virtual, joystick, app_config, mapping, trigger_key=None):
    # 🔥 เมื่อถูกเรียกจาก Sequence Engine: trigger_key = ชื่อมาโคร (เช่น "macro_3")
    #    ให้รันมาโครนั้นทันที โดยไม่ต้องอ่าน mapping จากจอย
    if trigger_key:
        macro_library = load_macro_library()
        sequence = macro_library.get(trigger_key)
        if sequence:
            for step in sequence:
                execute_step(ui_virtual, step)
                time.sleep(0.01)
            return True
        return False

    # 🔽 โหมดปกติ: อ่าน mapping จากจอย แล้วรันมาโครที่ผูกกับปุ่ม
    if not joystick or not mapping:
        return False
    if not hasattr(run, "_pressed_state"):
        run._pressed_state = {}

    macro_library = load_macro_library()

    # ดึงค่า Mapping ออกมาทั้งหมด
    all_mappings = {}
    all_mappings.update(mapping.get("buttons", {}))
    all_mappings.update(mapping.get("analogs", {}))

    for key_str, macro_name in all_mappings.items():
        try:
            # 1. ถอดรหัสข้อความ String ให้กลับเป็นตัวเลข/List/Dict
            try:
                parsed_key = ast.literal_eval(key_str)
            except (ValueError, SyntaxError):
                parsed_key = int(key_str)  # กรณีเป็นตัวเลขโดดๆ เช่น "9"

            # 2. เช็คว่า Input นั้นถูกกดอยู่หรือไม่
            is_active = is_input_active(joystick, parsed_key)

            # 3. สั่งรันมาโคร (ระบบ Just Pressed)
            _trigger_macro(ui_virtual, key_str, is_active, macro_name, macro_library)

        except Exception:
            continue

    return False
