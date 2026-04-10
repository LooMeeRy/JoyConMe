# menus/main_menu.py
from menus import keyboard_menu

MENU_ITEMS = ["ตั้งค่าปุ่ม", "ความเร็วเมาส์", "จัดการสูตรลับ", "คีย์บอร์ด", "ปิดเมนู"]


def run(selected_item, context):
    if selected_item == "ปิดเมนู":
        return "CLOSE_MENU"
    elif selected_item == "ตั้งค่าปุ่ม":
        return "SWITCH:button_main"
    elif selected_item == "ความเร็วเมาส์":
        return "SWITCH:mouse_main"
    elif selected_item == "จัดการสูตรลับ":
        return "SWITCH:cheat_main"
    elif selected_item == "คีย์บอร์ด":
        return keyboard_menu.run(selected_item, context)

    return None
