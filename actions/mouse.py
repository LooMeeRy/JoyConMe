import math

from evdev import ecodes as e

ACTION_INFO = {
    "id": "mouse_control",
    "name": "ควบคุมเมาส์และลูกกลิ้ง",
    "actions": [
        {"key": "move_x", "type": "analog", "desc": "ขยับเมาส์แนวนอน"},
        {"key": "move_y", "type": "analog", "desc": "ขยับเมาส์แนวตั้ง"},
        {"key": "scroll_y", "type": "analog", "desc": "ลูกกลิ้งเมาส์"},
        {"key": "left_click", "type": "button", "desc": "คลิกซ้าย"},
        {"key": "right_click", "type": "button", "desc": "คลิกขวา"},
        {
            "key": "focus_mode",
            "type": "button",
            "desc": "โหมดโฟกัส (ช้าพิเศษ)",
        },  # ✨ เพิ่ม Action ใหม่
    ],
}


def run(ui_virtual, joystick, app_config, mod_mapping):
    # 1. ดึงค่าตั้งค่าจาก app_config
    mouse_cfg = app_config.get("mouse", {})
    speed_x = mouse_cfg.get("speed_x", 15)
    speed_y = mouse_cfg.get("speed_y", 15)
    deadzone = mouse_cfg.get("deadzone", 0.15)

    # 2. ดึงการตั้งค่าปุ่มจาก mapping.json
    analogs = mod_mapping.get("analogs", {})
    buttons = mod_mapping.get("buttons", {})

    # --- ✨ ระบบ Focus Mode (Sniper Mode) ---
    # ถ้ากดปุ่ม focus_mode ค้างไว้ จะลดความเร็วลงเหลือ 1/5 (หรือ 0.2)
    current_multiplier = 1.0
    focus_btn = buttons.get("focus_mode")
    if focus_btn is not None and joystick.get_button(focus_btn):
        current_multiplier = 0.2  # 🐢 ปรับตรงนี้ได้ ถ้าอยากให้ช้าลงอีกก็ลดเลขลง (เช่น 0.1)

    # --- การขยับเมาส์ ---
    ax = analogs.get("move_x")
    ay = analogs.get("move_y")
    if ax is not None and ay is not None:
        val_x = joystick.get_axis(ax)
        val_y = joystick.get_axis(ay)

        # คำนวณความเร็วโดยคูณกับ current_multiplier
        dx = int(val_x * speed_x * current_multiplier) if abs(val_x) > deadzone else 0
        dy = int(val_y * speed_y * current_multiplier) if abs(val_y) > deadzone else 0

        if dx != 0 or dy != 0:
            ui_virtual.write(e.EV_REL, e.REL_X, dx)
            ui_virtual.write(e.EV_REL, e.REL_Y, dy)

    # --- ลูกกลิ้งเมาส์ ---
    ascr = analogs.get("scroll_y")
    if ascr is not None:
        val_scr = joystick.get_axis(ascr)
        if abs(val_scr) > 0.5:
            direction = -1 if val_scr > 0 else 1
            ui_virtual.write(e.EV_REL, e.REL_WHEEL, direction)

    # --- การคลิก ---
    if "left_click" in buttons:
        state = joystick.get_button(buttons["left_click"])
        ui_virtual.write(e.EV_KEY, e.BTN_LEFT, state)

    if "right_click" in buttons:
        state = joystick.get_button(buttons["right_click"])
        ui_virtual.write(e.EV_KEY, e.BTN_RIGHT, state)

    ui_virtual.syn()
