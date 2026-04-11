import os
import sys

import pygame

# --- Action Info ---
ACTION_INFO = {
    "id": "exit_app",
    "name": "ปิดโปรแกรม",
    "priority": 0,  # ✨ สูงสุดเพื่อให้ทำงานได้ตลอด
    "is_blocking": True,  # ✨ Bypass Shield ได้ (สั่งปิดได้แม้ล็อกเครื่อง)
    "actions": [{"key": "exit_now", "type": "button", "desc": "ปิดโปรแกรมทันที"}],
}


# --- Helper: ตรวจจับการกดปุ่ม (ใช้ร่วมกันได้ทุกรูปแบบ) ---
def is_pressed(joystick, mapping_val):
    if mapping_val is None:
        return False

    # 1. ปุ่มธรรมดา (Integer)
    if isinstance(mapping_val, int):
        try:
            return joystick.get_button(mapping_val)
        except:
            return False

    # 2. Hat / D-Pad (Dictionary)
    if isinstance(mapping_val, dict):
        if "hat" in mapping_val:
            try:
                h_id = mapping_val["hat"]
                target_dir = mapping_val["dir"]
                current_val = joystick.get_hat(h_id)
                if target_dir[0] != 0 and current_val[0] == target_dir[0]:
                    return True
                if target_dir[1] != 0 and current_val[1] == target_dir[1]:
                    return True
            except:
                pass
        return False

    # 3. Combo (List) - ต้องกดพร้อมกันทุกปุ่ม
    if isinstance(mapping_val, list):
        return all(is_pressed(joystick, item) for item in mapping_val)

    return False


# --- Main Run Function ---
def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    if not joystick:
        return False

    # 🟢 1. รับคำสั่งจาก "สูตรลับ" (Sequence Engine)
    # ถ้ามีการส่ง trigger_key มา และตรงกับ "exit_now" ให้ปิดทันที
    if trigger_key == "exit_now":
        print("🚨 [ExitApp] สั่งปิดโปรแกรมผ่านสูตรลับ!")
        return "EXIT"

    # 🔵 2. เช็คการกดปุ่มตาม Mapping ปกติ (ใน config)
    # ดึงค่าปุ่มจาก mod_mapping.get("buttons", {}).get("exit_now")
    btn_mapping = mod_mapping.get("buttons", {}).get("exit_now")

    if btn_mapping is not None:
        if is_pressed(joystick, btn_mapping):
            print("🚨 [ExitApp] สั่งปิดโปรแกรมผ่านปุ่ม Hotkey!")
            return "EXIT"

    return False
