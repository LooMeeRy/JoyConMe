# menus/macro_library.py
import time

from menus.utils import load_macros, save_macros

MENU_NAME = "คลังมาโคร"
MENU_TARGET = "macro_library"

# --- State & Temporary Data ---
state = "main"
target_macro_name = None
temp_sequence = []  # [ "a", ["ctrl", "c"], "enter" ]
combo_buffer = []  # สำหรับสร้างชุด Combo
keys_page = 0  # ✨ ตัวเก็บหน้าปัจจุบันของการเลือกคีย์
KEYS_PER_PAGE = 8  # ✨ จำนวนคีย์ที่แสดงต่อหนึ่งหน้า

# รายการคีย์ที่มีให้เลือกใช้งาน
KEYS_LIST = [
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "0",
    "ctrl",
    "shift",
    "alt",
    "space",
    "enter",
    "backspace",
    "tab",
    "esc",
    "up",
    "down",
    "left",
    "right",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
]

MENU_MAIN = ["➕ สร้างมาโครใหม่", "🔍 ดู/แก้ไข/ลบคลัง", "กลับ"]
MENU_EDIT_OPTS = ["+ เพิ่มคีย์เดี่ยว", "+ เพิ่ม Combo", "ล้างขั้นตอน", "💾 บันทึกมาโคร", "ยกเลิก"]
MENU_CONFIRM = ["ยกเลิก", "ยืนยัน"]


def reset():
    global state, target_macro_name, temp_sequence, combo_buffer, keys_page
    state = "main"
    target_macro_name = None
    temp_sequence = []
    combo_buffer = []
    keys_page = 0


def get_keys_menu():
    """✨ ฟังก์ชันช่วยสร้างรายการคีย์แบบแบ่งหน้า"""
    global keys_page
    start = keys_page * KEYS_PER_PAGE
    end = start + KEYS_PER_PAGE
    current_keys = KEYS_LIST[start:end]

    menu = []
    # เพิ่มปุ่มพิเศษตามสถานะ
    if state == "pick_combo":
        menu.append("✅ เสร็จสิ้นชุด Combo")

    menu.extend(current_keys)

    if keys_page > 0:
        menu.append("⬅️ ก่อนหน้า")
    if end < len(KEYS_LIST):
        menu.append("ถัดไป ➡️")

    menu.append("ยกเลิก")
    return menu


def get_sequence_preview():
    if not temp_sequence:
        return "(ว่างเปล่า)"
    parts = []
    for s in temp_sequence:
        if isinstance(s, list):
            parts.append(f"[{'+'.join(s)}]")
        else:
            parts.append(s)
    return " ➔ ".join(parts)


def run(selected_item, context):
    global state, target_macro_name, temp_sequence, combo_buffer, keys_page
    overlay = context["overlay"]
    macros = load_macros()

    # --- หน้าหลัก ---
    if state == "main":
        if selected_item == "กลับ":
            return "SWITCH:main"
        elif selected_item == "➕ สร้างมาโครใหม่":
            target_macro_name = f"macro_{len(macros) + 1}"
            temp_sequence = []
            state = "editing"
            overlay.menu_items = MENU_EDIT_OPTS
            overlay.center_msg = f"สร้าง: {target_macro_name}\n{get_sequence_preview()}"
            return "UPDATE_UI"
        elif selected_item == "🔍 ดู/แก้ไข/ลบคลัง":
            if not macros:
                overlay.center_msg = "คลังว่างเปล่า!"
                return "UPDATE_UI"
            state = "list_macros"
            overlay.menu_items = list(macros.keys()) + ["กลับ"]
            return "UPDATE_UI"

    # --- หน้ารายการมาโคร ---
    elif state == "list_macros":
        if selected_item == "กลับ":
            state = "main"
            overlay.menu_items = MENU_MAIN
        else:
            target_macro_name = selected_item
            state = "macro_options"
            # โหลด Sequence มาเก็บไว้เลย จะได้โชว์ Preview ได้ทันที
            temp_sequence = macros.get(target_macro_name, [])
            overlay.menu_items = ["แก้ไขขั้นตอน", "❌ ลบมาโครนี้", "กลับ"]
            overlay.center_msg = f"มาโคร: {target_macro_name}\n{get_sequence_preview()}"
        return "UPDATE_UI"

    # --- 🚨 เมนูย่อยของมาโครที่เลือก (ส่วนที่หายไป) 🚨 ---
    elif state == "macro_options":
        if selected_item == "กลับ":
            state = "list_macros"
            overlay.menu_items = list(macros.keys()) + ["กลับ"]
            return "UPDATE_UI"
        elif selected_item == "แก้ไขขั้นตอน":
            state = "editing"
            overlay.menu_items = MENU_EDIT_OPTS
            return "UPDATE_UI"
        elif selected_item == "❌ ลบมาโครนี้":
            state = "confirm_delete"
            overlay.menu_items = MENU_CONFIRM
            overlay.center_msg = f"ยืนยันลบ {target_macro_name}?"
            return "UPDATE_UI"

    # --- หน้าแก้ไข (ต่อรถไฟ) ---
    elif state == "editing":
        overlay.center_msg = f"แก้ไข: {target_macro_name}\n{get_sequence_preview()}"
        if selected_item == "ยกเลิก":
            reset()
            overlay.menu_items = MENU_MAIN
        elif selected_item == "+ เพิ่มคีย์เดี่ยว":
            state = "pick_single"
            keys_page = 0
            overlay.menu_items = get_keys_menu()
        elif selected_item == "+ เพิ่ม Combo":
            state = "pick_combo"
            keys_page = 0
            combo_buffer = []
            overlay.menu_items = get_keys_menu()
        elif selected_item == "ล้างขั้นตอน":
            temp_sequence = []
        elif selected_item == "💾 บันทึกมาโคร":
            macros[target_macro_name] = temp_sequence
            save_macros(macros)
            overlay.center_msg = f"บันทึก {target_macro_name} แล้ว!"
            reset()
            overlay.menu_items = MENU_MAIN
        return "UPDATE_UI"

    # --- หน้าเลือกคีย์ (Single & Combo) ---
    elif state in ["pick_single", "pick_combo"]:
        if selected_item == "ยกเลิก":
            state = "editing"
            overlay.menu_items = MENU_EDIT_OPTS
            return "UPDATE_UI"

        elif selected_item == "ถัดไป ➡️":
            keys_page += 1
            overlay.menu_items = get_keys_menu()
            return "UPDATE_UI"

        elif selected_item == "⬅️ ก่อนหน้า":
            keys_page -= 1
            overlay.menu_items = get_keys_menu()
            return "UPDATE_UI"

        elif selected_item == "✅ เสร็จสิ้นชุด Combo":
            if combo_buffer:
                temp_sequence.append(combo_buffer)
            state = "editing"
            overlay.menu_items = MENU_EDIT_OPTS
            return "UPDATE_UI"

        else:
            # เลือกคีย์
            if state == "pick_single":
                temp_sequence.append(selected_item)
                state = "editing"
                overlay.menu_items = MENU_EDIT_OPTS
            else:
                # โหมด Combo
                if selected_item not in combo_buffer:
                    combo_buffer.append(selected_item)
                overlay.center_msg = f"Combo: {' + '.join(combo_buffer)}"
            return "UPDATE_UI"

    # --- ยืนยันการลบ ---
    elif state == "confirm_delete":
        if selected_item == "ยืนยัน":
            if target_macro_name in macros:
                del macros[target_macro_name]
                save_macros(macros)
            overlay.center_msg = "ลบมาโครแล้ว"
        reset()
        overlay.menu_items = MENU_MAIN
        return "UPDATE_UI"

    return None
