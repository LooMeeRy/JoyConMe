import time

import pyautogui
from pynput.keyboard import Controller, Key

# --- Action Info ---
ACTION_INFO = {
    "id": "system_control",
    "name": "ควบคุมระบบเครื่อง",
    "priority": 50,
    "actions": [
        {"key": "vol_up", "type": "button", "desc": "เพิ่มเสียง"},
        {"key": "vol_down", "type": "button", "desc": "ลดเสียง"},
        {"key": "vol_mute", "type": "button", "desc": "ปิด/เปิดเสียง (Mute)"},
        {"key": "screenshot", "type": "button", "desc": "แคปหน้าจอ"},
        {"key": "media_play", "type": "button", "desc": "เล่น/หยุด เพลง"},
        {"key": "media_next", "type": "button", "desc": "เพลงถัดไป"},
    ],
}

_last_execution_time = 0
_DEBOUNCE_DELAY = 0.3
_keyboard = Controller()  # จำลองคีย์บอร์ดแบบ Cross-platform


def is_triggered(joystick, val):
    if val is None:
        return False
    if isinstance(val, int):
        try:
            return joystick.get_button(val)
        except:
            return False
    if isinstance(val, list):
        return all(is_triggered(joystick, item) for item in val)
    if isinstance(val, dict) and "hat" in val:
        try:
            h_id = val["hat"]
            target_dir = val["dir"]
            current_val = joystick.get_hat(h_id)
            if target_dir[0] != 0:
                return current_val[0] == target_dir[0]
            if target_dir[1] != 0:
                return current_val[1] == target_dir[1]
        except:
            pass
    return False


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    global _last_execution_time
    key = trigger_key
    current_time = time.time()

    if key is None and joystick and mod_mapping:
        if current_time - _last_execution_time < _DEBOUNCE_DELAY:
            return False
        for act in ACTION_INFO["actions"]:
            mapping_val = mod_mapping.get("buttons", {}).get(act["key"])
            if mapping_val is not None:
                if is_triggered(joystick, mapping_val):
                    key = act["key"]
                    _last_execution_time = current_time
                    break

    if key is None:
        return False

    # --- ส่วนสั่งงานระบบแบบ Cross-Platform ---
    try:
        if key == "vol_up":
            _keyboard.press(Key.media_volume_up)
            _keyboard.release(Key.media_volume_up)
        elif key == "vol_down":
            _keyboard.press(Key.media_volume_down)
            _keyboard.release(Key.media_volume_down)
        elif key == "vol_mute":
            _keyboard.press(Key.media_volume_mute)
            _keyboard.release(Key.media_volume_mute)
        elif key == "media_play":
            _keyboard.press(Key.media_play_pause)
            _keyboard.release(Key.media_play_pause)
        elif key == "media_next":
            _keyboard.press(Key.media_next_track)
            _keyboard.release(Key.media_next_track)
        elif key == "screenshot":
            # สร้างชื่อไฟล์จาก Timestamp ป้องกันการเซฟทับ
            filename = f"screenshot_{int(time.time())}.png"
            pyautogui.screenshot(filename)
            print(f"📸 บันทึกภาพหน้าจอ: {filename}")

    except Exception as e:
        print(f"⚠️ System Control Error: {e}")

    return True
