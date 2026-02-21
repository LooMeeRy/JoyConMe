import math
import os
import time

import pygame
from evdev import ecodes as e

# --- Action Info ---
ACTION_INFO = {
    "id": "mouse_control",
    "name": "ควบคุมเมาส์",
    "actions": [
        {"key": "move_x", "type": "analog", "desc": "ขยับแกน X"},
        {"key": "move_y", "type": "analog", "desc": "ขยับแกน Y"},
        {"key": "scroll_y", "type": "analog", "desc": "เลื่อน Scroll"},
        {"key": "left_click", "type": "button", "desc": "คลิกซ้าย"},
        {"key": "right_click", "type": "button", "desc": "คลิกขวา"},
        {
            "key": "focus",
            "type": "button",
            "desc": "โฟกัส (ชะลอเมาส์)",
        },  # ✨ เพิ่ม Action นี้
    ],
}

# --- State Variables ---
_left_is_pressed = False
_right_is_pressed = False


# --- Helper ---
def load_config():
    path = os.path.join("config", "config.json")
    if not os.path.exists(path):
        return {}
    try:
        import json

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


# --- Main Run Function ---
def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    global _left_is_pressed, _right_is_pressed

    # 1. Trigger Mode (สูตรลับ)
    if trigger_key is not None:
        if trigger_key == "left_click":
            ui_virtual.write(e.EV_KEY, e.BTN_LEFT, 1)
            ui_virtual.syn()
            time.sleep(0.05)
            ui_virtual.write(e.EV_KEY, e.BTN_LEFT, 0)
            ui_virtual.syn()
            return
        elif trigger_key == "right_click":
            ui_virtual.write(e.EV_KEY, e.BTN_RIGHT, 1)
            ui_virtual.syn()
            time.sleep(0.05)
            ui_virtual.write(e.EV_KEY, e.BTN_RIGHT, 0)
            ui_virtual.syn()
            return
        # Focus ไม่ควรถูกเรียกแบบ Trigger เพราะมันคือการกดค้าง แต่ถ้าสูตรเรียกก็ให้ผ่านไป
        return

    # 2. Normal Mode
    if not joystick:
        return

    if not app_config:
        app_config = load_config()
    mouse_cfg = app_config.get("mouse", {})
    speed_x = mouse_cfg.get("speed_x", 20)
    speed_y = mouse_cfg.get("speed_y", 20)

    # ✨ Logic ตรวจจับ Focus (กดค้างเพื่อชะลอ)
    is_focusing = False
    if "focus" in mod_mapping.get("buttons", {}):
        btn_idx = mod_mapping["buttons"]["focus"]
        try:
            if joystick.get_button(btn_idx):
                is_focusing = True
                # ลดความเร็วลง 3 เท่าตอน Focus
                speed_x = max(1, int(speed_x * 0.3))
                speed_y = max(1, int(speed_y * 0.3))
        except:
            pass

    # --- Movement ---
    if "move_x" in mod_mapping.get("analogs", {}):
        try:
            axis_idx = mod_mapping["analogs"]["move_x"]
            val = joystick.get_axis(axis_idx)
            if abs(val) > 0.15:
                move_val = int(val * speed_x)
                if move_val != 0:
                    ui_virtual.write(e.EV_REL, e.REL_X, move_val)
        except:
            pass

    if "move_y" in mod_mapping.get("analogs", {}):
        try:
            axis_idx = mod_mapping["analogs"]["move_y"]
            val = joystick.get_axis(axis_idx)
            if abs(val) > 0.15:
                move_val = int(val * speed_y)
                if move_val != 0:
                    ui_virtual.write(e.EV_REL, e.REL_Y, move_val)
        except:
            pass

    # Scroll
    if "scroll_y" in mod_mapping.get("analogs", {}):
        try:
            axis_idx = mod_mapping["analogs"]["scroll_y"]
            val = joystick.get_axis(axis_idx)
            if abs(val) > 0.7:
                scroll_amount = -1 if val > 0 else 1
                ui_virtual.write(e.EV_REL, e.REL_WHEEL, scroll_amount)
        except:
            pass

    ui_virtual.syn()

    # --- Button Clicks (State Machine) ---
    # Left Click
    if "left_click" in mod_mapping.get("buttons", {}):
        try:
            btn_idx = mod_mapping["buttons"]["left_click"]
            is_down = joystick.get_button(btn_idx)

            if is_down and not _left_is_pressed:
                ui_virtual.write(e.EV_KEY, e.BTN_LEFT, 1)
                ui_virtual.syn()
                _left_is_pressed = True
            elif not is_down and _left_is_pressed:
                ui_virtual.write(e.EV_KEY, e.BTN_LEFT, 0)
                ui_virtual.syn()
                _left_is_pressed = False
        except:
            pass

    # Right Click
    if "right_click" in mod_mapping.get("buttons", {}):
        try:
            btn_idx = mod_mapping["buttons"]["right_click"]
            is_down = joystick.get_button(btn_idx)

            if is_down and not _right_is_pressed:
                ui_virtual.write(e.EV_KEY, e.BTN_RIGHT, 1)
                ui_virtual.syn()
                _right_is_pressed = True
            elif not is_down and _right_is_pressed:
                ui_virtual.write(e.EV_KEY, e.BTN_RIGHT, 0)
                ui_virtual.syn()
                _right_is_pressed = False
        except:
            pass
