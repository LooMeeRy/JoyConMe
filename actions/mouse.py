import os
import time

import pygame
from evdev import ecodes as e

# --- Action Info ---
ACTION_INFO = {
    "id": "mouse",
    "name": "ควบคุมเมาส์",
    "priority": 100,
    "is_blocking": False,
    "actions": [
        {"key": "move_x", "type": "analog", "desc": "ขยับแกน X"},
        {"key": "move_y", "type": "analog", "desc": "ขยับแกน Y"},
        {"key": "scroll_y", "type": "analog", "desc": "เลื่อน Scroll"},
        {"key": "left_click", "type": "button", "desc": "คลิกซ้าย"},
        {"key": "right_click", "type": "button", "desc": "คลิกขวา"},
        {"key": "focus", "type": "button", "desc": "โฟกัส (ชะลอเมาส์)"},
    ],
}

# --- State Variables ---
_left_is_pressed = False
_right_is_pressed = False


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    global _left_is_pressed, _right_is_pressed

    if not joystick or not ui_virtual:
        return

    # 1. Trigger Mode (สูตรลับ)
    if trigger_key is not None:
        if trigger_key == "left_click":
            ui_virtual.write(e.EV_KEY, e.BTN_LEFT, 1)
            ui_virtual.syn()
            time.sleep(0.05)
            ui_virtual.write(e.EV_KEY, e.BTN_LEFT, 0)
            ui_virtual.syn()
        elif trigger_key == "right_click":
            ui_virtual.write(e.EV_KEY, e.BTN_RIGHT, 1)
            ui_virtual.syn()
            time.sleep(0.05)
            ui_virtual.write(e.EV_KEY, e.BTN_RIGHT, 0)
            ui_virtual.syn()
        return

    # 2. ดึงค่า Config ความเร็ว
    mouse_cfg = app_config.get("mouse", {})
    speed_x = mouse_cfg.get("speed_x", 20)
    speed_y = mouse_cfg.get("speed_y", 20)

    # 3. Logic ตรวจจับ Focus (ชะลอเมาส์)
    if "focus" in mod_mapping.get("buttons", {}):
        try:
            if joystick.get_button(mod_mapping["buttons"]["focus"]):
                speed_x = max(1, int(speed_x * 0.3))
                speed_y = max(1, int(speed_y * 0.3))
        except:
            pass

    # --- Movement (X, Y) ---
    moved = False
    if "move_x" in mod_mapping.get("analogs", {}):
        try:
            val = joystick.get_axis(mod_mapping["analogs"]["move_x"])
            if abs(val) > 0.15:
                ui_virtual.write(e.EV_REL, e.REL_X, int(val * speed_x))
                moved = True
        except:
            pass

    if "move_y" in mod_mapping.get("analogs", {}):
        try:
            val = joystick.get_axis(mod_mapping["analogs"]["move_y"])
            if abs(val) > 0.15:
                ui_virtual.write(e.EV_REL, e.REL_Y, int(val * speed_y))
                moved = True
        except:
            pass

    # --- Scroll ---
    if "scroll_y" in mod_mapping.get("analogs", {}):
        try:
            val = joystick.get_axis(mod_mapping["analogs"]["scroll_y"])
            if abs(val) > 0.5:
                ui_virtual.write(e.EV_REL, e.REL_WHEEL, 1 if val < 0 else -1)
                moved = True
        except:
            pass

    # --- Button Clicks ---
    # Left Click
    if "left_click" in mod_mapping.get("buttons", {}):
        try:
            is_down = joystick.get_button(mod_mapping["buttons"]["left_click"])
            if is_down != _left_is_pressed:
                ui_virtual.write(e.EV_KEY, e.BTN_LEFT, 1 if is_down else 0)
                _left_is_pressed = is_down
                moved = True
        except:
            pass

    # Right Click
    if "right_click" in mod_mapping.get("buttons", {}):
        try:
            is_down = joystick.get_button(mod_mapping["buttons"]["right_click"])
            if is_down != _right_is_pressed:
                ui_virtual.write(e.EV_KEY, e.BTN_RIGHT, 1 if is_down else 0)
                _right_is_pressed = is_down
                moved = True
        except:
            pass

    # สำคัญ: ถ้ามีการขยับหรือคลิก ต้องส่งสัญญาณ SYN
    if moved:
        ui_virtual.syn()
