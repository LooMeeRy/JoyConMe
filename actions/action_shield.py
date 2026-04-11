import json
import os

# --- Action Info ---
ACTION_INFO = {
    "id": "action_shield",
    "name": "ระบบล็อก Action (Shield)",
    "priority": 1,  # ✨ อยู่ในกลุ่ม System (รันก่อน Mouse/Keyboard)
    "is_blocking": True,  # ✨ สำคัญ: ต้องเป็น True เพื่อให้ Bypass Shield ได้ในระดับ Engine
    "actions": [
        {"key": "toggle_shield", "type": "button", "desc": "เปิด/ปิด การล็อก Action ทั้งหมด"}
    ],
}


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    """
    ฟังก์ชันหลักสำหรับสลับสถานะเกราะป้องกัน (Shield)
    """
    # 🚨 ตรวจสอบการเรียกใช้งาน (ผ่านสูตรลับ หรือ ปุ่ม Hotkey)
    if trigger_key == "toggle_shield":
        # 1. เข้าถึงตำแหน่งข้อมูลใน Config
        if "system" not in app_config:
            app_config["system"] = {}

        # 2. อ่านค่าปัจจุบัน (ถ้าไม่มีให้ถือว่าเป็น False)
        current_status = app_config["system"].get("action_shield", False)

        # 3. สลับสถานะ (Toggle)
        new_status = not current_status
        app_config["system"]["action_shield"] = new_status

        # 4. แสดงผลแจ้งเตือนใน Console
        # status_msg = (
        #     "🔒 SHIELD ACTIVE (Locked)"
        #     if new_status
        #     else "🔓 SHIELD INACTIVE (Unlocked)"
        # )
        # print(f"\n🛡️ [ActionShield] {status_msg}")

        # 🚨 หัวใจสำคัญ: ส่งสัญญาณ SAVE_CONFIG กลับไปหา Engine
        # เพื่อให้ Engine เรียกฟังก์ชัน save_app_config() และอัปเดตสถานะใน RAM ทันที
        return "SAVE_CONFIG"

    # กรณีรันปกติ (ไม่ได้ถูก Trigger) ให้คืน False
    return False
