import json
import os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))


def load_json(filename):
    """โหลดข้อมูลจากไฟล์ JSON เท่านั้น"""
    filepath = os.path.join(CONFIG_DIR, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"ไม่พบไฟล์ {filename} ระบบอาจจะ setup ไม่สมบูรณ์")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
