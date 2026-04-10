# menus/keyboard_menu.py
from actions import keyboard

MENU_NAME = "คีย์บอร์ด"


def run(selected_item, context):
    keyboard._controller.open()
    return "CLOSE_MENU"
