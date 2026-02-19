import json
import os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

# เก็บค่า Default ไว้ที่นี่ที่เดียว
DEFAULT_CONFIG = {
    "mouse": {"deadzone": 0.1, "speed_x": 10, "speed_y": 10},
    "system": {"sleep_time": 0.01},
}

DEFAULT_MAPPING = {
    "mouse_control": {
        "analogs": {"move_x": 0, "move_y": 1},
        "buttons": {"left_click": 0, "right_click": 1},
    }
}


def create_if_not_exists(filename, default_data):
    filepath = os.path.join(CONFIG_DIR, filename)
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4)
        print(f"[Setup] สร้างไฟล์ {filename} เริ่มต้นเรียบร้อยแล้ว")


def initialize_configs():
    """ฟังก์ชันนี้จะถูกเรียกตอนเริ่มรันโปรแกรม เพื่อเตรียมไฟล์ให้พร้อม"""
    create_if_not_exists("config.json", DEFAULT_CONFIG)
    create_if_not_exists("mapping.json", DEFAULT_MAPPING)
