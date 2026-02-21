# menus/main_menu.py
import pygame

MENU_ITEMS = ["ตั้งค่าปุ่ม", "ความเร็วเมาส์", "จัดการสูตรลับ", "ปิดเมนู"]


def run(selected_item, context):
    overlay = context["overlay"]

    if selected_item == "ปิดเมนู":
        return "CLOSE_MENU"
    elif selected_item == "ตั้งค่าปุ่ม":
        return "SWITCH:button_main"
    elif selected_item == "ความเร็วเมาส์":
        return "SWITCH:mouse_main"
    elif selected_item == "จัดการสูตรลับ":
        return "SWITCH:cheat_main"

    return None
