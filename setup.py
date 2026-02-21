import json
import os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONFIG = {
    "mouse": {"speed_x": 25, "speed_y": 25, "deadzone": 0.15, "scroll_delay": 0.08},
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
        "buttons": {"right_click": 1, "left_click": 0, "focus_mode": 9},
    },
    "radial_setup": {"buttons": {"open_menu": [10, 11]}},
    "sequence_engine": {"analogs": {}, "buttons": {"open_listener": [7, 10]}},
}


def create_if_not_exists(filename, default_data):
    filepath = os.path.join(CONFIG_DIR, filename)
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4)
        print(f"[Setup] Created {filename}")


def initialize_configs():
    create_if_not_exists("config.json", DEFAULT_CONFIG)
    create_if_not_exists("mapping.json", DEFAULT_MAPPING)
