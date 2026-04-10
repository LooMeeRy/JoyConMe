import subprocess
import time

# --- Action Info ---
ACTION_INFO = {
    "id": "system_control",
    "name": "ควบคุมระบบเครื่อง",
    "actions": [
        {"key": "vol_up", "type": "button", "desc": "เพิ่มเสียง +5%"},
        {"key": "vol_down", "type": "button", "desc": "ลดเสียง -5%"},
        {"key": "vol_mute", "type": "button", "desc": "ปิด/เปิดเสียง (Mute)"},
        {"key": "screenshot", "type": "button", "desc": "แคปหน้าจอ (Area)"},
        {"key": "media_play", "type": "button", "desc": "เล่น/หยุด เพลง"},
        {"key": "media_next", "type": "button", "desc": "เพลงถัดไป"},
    ],
}

_last_execution_time = 0
_DEBOUNCE_DELAY = 0.3  # เพิ่ม Delay เป็น 0.3 วินาที เพื่อกันการกดเบิ้ล


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


def run_cmd(cmd_list):
    try:
        subprocess.run(cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
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

    # --- ส่วนสั่งงานระบบ ---
    if key == "vol_up":
        run_cmd(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"])
    elif key == "vol_down":
        run_cmd(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"])
    elif key == "vol_mute":
        run_cmd(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
    elif key == "screenshot":
        run_cmd(["spectacle", "-r", "-b"])

    elif key == "media_play":
        # 🎵 ใช้ playerctl play-pause เพียงอย่างเดียว และระบุ -a เพื่อคุมทุกตัว
        # การไม่ใช้ Virtual Key ร่วมด้วยจะช่วยลดปัญหาการ "กดเบิ้ล" ในระดับซอฟต์แวร์ครับ
        run_cmd(["playerctl", "play-pause", "-a"])

    elif key == "media_next":
        run_cmd(["playerctl", "next", "-a"])

    return True
