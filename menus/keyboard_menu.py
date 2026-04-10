# menus/keyboard_menu.py
from actions import keyboard


def run(selected_item, context):
    keyboard._controller.open()
    return "CLOSE_MENU"
