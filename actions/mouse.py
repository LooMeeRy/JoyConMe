# actions/mouse.py
import time

from evdev import ecodes as e

ACTION_INFO = {
    "id": "mouse_control",
    "name": "ควบคุมเมาส์",
    "actions": [
        {"key": "move_x", "type": "analog", "desc": "ขยับเมาส์แนวนอน (ซ้าย-ขวา)"},
        {"key": "move_y", "type": "analog", "desc": "ขยับเมาส์แนวตั้ง (บน-ล่าง)"},
        {
            "key": "scroll_y",
            "type": "analog",
            "desc": "ลูกกลิ้งเมาส์ (Scroll ขึ้น-ลง)",
        },  # ✨ เพิ่มบรรทัดนี้
        {"key": "left_click", "type": "button", "desc": "คลิกซ้าย"},
        {"key": "right_click", "type": "button", "desc": "คลิกขวา"},
    ],
}

# ตัวแปรจำเวลาของลูกกลิ้ง เพื่อไม่ให้มันเลื่อนรัวเกินไป
last_scroll_time = 0
base_scroll_delay = 0.08  # ปรับค่าน้อยลง = เลื่อนเร็วขึ้น


def process_mouse_movement(ui, joystick, mouse_config, analog_mapping, button_mapping):
    global last_scroll_time

    # --- ส่วนการขยับเมาส์ (Analog) ---
    axis_x_id = analog_mapping.get("move_x")
    axis_y_id = analog_mapping.get("move_y")

    deadzone = mouse_config.get("deadzone", 0.1)
    speed_x = mouse_config.get("speed_x", 15)
    speed_y = mouse_config.get("speed_y", 15)

    move_x = 0
    move_y = 0

    if axis_x_id is not None:
        val_x = joystick.get_axis(axis_x_id)
        if abs(val_x) > deadzone:
            move_x = int(val_x * speed_x)

    if axis_y_id is not None:
        val_y = joystick.get_axis(axis_y_id)
        if abs(val_y) > deadzone:
            move_y = int(val_y * speed_y)

    if move_x != 0 or move_y != 0:
        ui.write(e.EV_REL, e.REL_X, move_x)
        ui.write(e.EV_REL, e.REL_Y, move_y)

    # --- ✨ ส่วนลูกกลิ้งเมาส์ (Analog Scroll) ---
    scroll_y_id = analog_mapping.get("scroll_y")
    if scroll_y_id is not None:
        val_scroll = joystick.get_axis(scroll_y_id)
        if abs(val_scroll) > deadzone:
            current_time = time.time()
            # ยิ่งดันอนาล็อกแรง ดีเลย์จะยิ่งน้อย = ไถเร็วขึ้น!
            dynamic_delay = base_scroll_delay / abs(val_scroll)

            if current_time - last_scroll_time > dynamic_delay:
                # ใน evdev: REL_WHEEL 1 คือดันขึ้น, -1 คือดันลง
                # อนาล็อกดันขึ้น(ค่าลบ) -> สั่ง scroll 1 (ขึ้น)
                direction = 1 if val_scroll < 0 else -1
                ui.write(e.EV_REL, e.REL_WHEEL, direction)
                last_scroll_time = current_time

    # --- ส่วนการคลิก (Button) ---
    # ตรวจสอบปุ่มคลิกซ้าย
    left_id = button_mapping.get("left_click")
    if left_id is not None:
        # ส่งสถานะปุ่มจอย (0 หรือ 1) ไปเป็นสถานะปุ่มเมาส์ (Press/Release)
        ui.write(e.EV_KEY, e.BTN_LEFT, joystick.get_button(left_id))

    # ตรวจสอบปุ่มคลิกขวา
    right_id = button_mapping.get("right_click")
    if right_id is not None:
        ui.write(e.EV_KEY, e.BTN_RIGHT, joystick.get_button(right_id))

    # อัปเดตสถานะทั้งหมดไปที่ Kernel ทีเดียว
    ui.syn()
