# menus/mouse_menu.py
import json
import os

from menus.utils import load_config, save_config

MENU_ITEMS = ["ช้า (5)", "ปกติ (15)", "เร็ว (25)", "ติดจรวด (40)", "กลับ"]


def run(selected_item, context):
    overlay = context["overlay"]
    app_config = context["app_config"]

    if selected_item == "กลับ":
        return "SWITCH:main"

    try:
        speed = int(selected_item.split("(")[1].split(")")[0])
        app_config["mouse"]["speed_x"] = speed
        app_config["mouse"]["speed_y"] = speed
        save_config(app_config)
        overlay.center_msg = f"ตั้งค่า: {speed}"
        # ไม่ต้อง switch state ไปไหน แสดงผลแล้วจบ
    except:
        pass

    return None
