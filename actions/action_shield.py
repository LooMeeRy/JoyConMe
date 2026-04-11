import time

ACTION_INFO = {
    "id": "action_shield",
    "name": "ระบบล็อก Action (Shield)",
    "priority": 95,  # 🌟 Priority สูงกว่าเมาส์และคีย์บอร์ด (แต่ต่ำกว่าเมนูตั้งค่า)
    "is_blocking": True,  # 🌟 สำคัญมาก: บอก Engine ว่าถ้าทำงานอยู่ ให้บล็อกตัวอื่น
    "actions": [
        {
            "key": "toggle_shield",
            "type": "button",
            "desc": "เปิด/ปิด การทำงาน Action อื่นทั้งหมด",
        }
    ],
}

# --- State Variables ---
# เก็บสถานะไว้ในหน่วยความจำ ไม่ต้องอ่าน/เขียนลงไฟล์
_is_shield_active = False
_btn_prev = False  # ตัวแปรดักจับไม่ให้ปุ่มทำงานรัวๆ เวลากดค้าง


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    global _is_shield_active, _btn_prev

    # --- 1. เช็คจากการถูกเรียกผ่านสูตรลับ (Trigger Key) ---
    if trigger_key == "toggle_shield":
        _is_shield_active = not _is_shield_active
        # print(
        #     f"\n🛡️ Action Shield: {'🔴 เปิดใช้งาน (LOCK)' if _is_shield_active else '🟢 ปิดใช้งาน (UNLOCK)'}"
        # )
        return _is_shield_active

    # --- 2. เช็คจากการกดปุ่มปกติที่ตั้งไว้ใน mapping.json ---
    if joystick and mod_mapping:
        btn_idx = mod_mapping.get("buttons", {}).get("toggle_shield")

        if btn_idx is not None:
            try:
                # อ่านค่าปุ่มจากจอยสติ๊ก
                is_pressed = joystick.get_button(btn_idx)

                # เช็คแบบ "Just Pressed" (เพิ่งถูกกดลงไป 1 ครั้งเท่านั้น)
                if is_pressed and not _btn_prev:
                    _is_shield_active = not _is_shield_active
                    # print(
                    #     f"\n🛡️ Action Shield: {'🔴 เปิดใช้งาน (LOCK)' if _is_shield_active else '🟢 ปิดใช้งาน (UNLOCK)'}"
                    # )

                # บันทึกสถานะการกดไว้เช็คในรอบถัดไป
                _btn_prev = is_pressed
            except Exception as e:
                pass

    # --- 3. การทำงานของ Shield (บล็อก/ไม่บล็อก) ---
    if _is_shield_active:
        # 🔴 ถ้าโล่ถูกเปิดใช้งานอยู่ ให้ return True
        # Engine จะเห็น True + is_blocking=True แล้วจะหยุด Action อื่นๆ ทันที
        return True

    # 🟢 ถ้าไม่ได้เปิดโล่ return False
    # Engine จะปล่อยผ่านให้เมาส์และ Action อื่นๆ ทำงานต่อไปตามปกติ
    return False
