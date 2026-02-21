import os
import sys

import pygame

# --- Action Info ---
ACTION_INFO = {
    "id": "exit_app",
    "name": "ปิดโปรแกรม",
    "actions": [{"key": "exit_now", "type": "button", "desc": "ปิดโปรแกรมทันที"}],
}


# --- Helper: ตรวจจับการกดปุ่มแบบครบครัน (แก้ไข Error) ---
def is_pressed(joystick, mapping_val):
    """
    ตรวจสอบการกดปุ่มแบบ Recursive
    รองรับ: int (ปุ่ม), dict (Hat/Dpad), list (Combo ผสม)
    """
    if mapping_val is None:
        return False

    # Case 1: ปุ่มธรรมดา (Integer)
    if isinstance(mapping_val, int):
        try:
            return joystick.get_button(mapping_val)
        except:
            return False

    # Case 2: Hat / D-Pad (Dictionary)
    if isinstance(mapping_val, dict):
        if "hat" in mapping_val:
            try:
                h_id = mapping_val["hat"]
                target_dir = mapping_val["dir"]
                current_val = joystick.get_hat(h_id)
                # เช็คทิศทาง
                if target_dir[0] != 0 and current_val[0] == target_dir[0]:
                    return True
                if target_dir[1] != 0 and current_val[1] == target_dir[1]:
                    return True
            except:
                pass
        return False

    # Case 3: Combo (List)
    if isinstance(mapping_val, list):
        # ต้องกดทุกปุ่มใน List (AND logic)
        # ใช้ Recursive เพื่อตรวจสอบ item ใน list แต่ละตัว (อาจเป็น int หรือ dict)
        return all(is_pressed(joystick, item) for item in mapping_val)

    return False


# --- ฟังก์ชันสั่งปิดโปรแกรม ---
def do_exit(ui_virtual):
    print("[ExitApp] Closing application...")
    if ui_virtual:
        try:
            ui_virtual.close()
        except:
            pass
    pygame.quit()
    sys.exit(0)


# --- Main Run Function ---
def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    """
    ทำงานได้ 2 กรณี:
    1. Trigger Mode: ถูกเรียกจาก Sequence Engine (สูตรลับ)
    2. Normal Mode: ผู้ใช้กดปุ่มที่ตั้งค่าไว้ใน mapping.json
    """

    # === Case 1: Trigger Mode (สูตรลับ) ===
    if trigger_key == "exit_now":
        do_exit(ui_virtual)
        return

    # === Case 2: Normal Mode (กดปุ่มปกติ) ===
    if not joystick:
        return

    # ดึงค่า mapping ออกมา (อาจเป็น int, dict, หรือ list)
    btn_mapping = mod_mapping.get("buttons", {}).get("exit_now")

    if btn_mapping is not None:
        if is_pressed(joystick, btn_mapping):
            do_exit(ui_virtual)
