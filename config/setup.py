import json
import os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

# เก็บค่า Default ไว้ที่นี่ที่เดียว
DEFAULT_CONFIG = {
    "mouse": {"speed_x": 15, "speed_y": 15, "deadzone": 0.15, "scroll_delay": 0.08},
    "ui": {
        "items_per_page": 6,
        "menu_radius": 220,
        "selection_threshold": 0.4,
        "wait_time_ms": 300,
        "opacity": 210,
    },
}


DEFAULT_MAPPING = {
    "mouse_control": {
        "analogs": {"move_x": 0, "move_y": 1, "scroll_y": 3},
        "buttons": {"right_click": 1, "left_click": 0},
    },
    "radial_setup": {"buttons": {"open_menu": 10}},
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
