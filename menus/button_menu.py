import time

import pygame

MENU_NAME = "ตั้งค่าปุ่ม"
MENU_TARGET = "button_main"

from menus.utils import (
    format_button_name,
    get_all_available_actions,
    load_mapping,
    save_mapping,
)

# --- State Management ---
state = "main"
edit_list = []
edit_page = 0
target_item = None
pending_action = None
new_input_val = None
new_action_val = None
selected_cat = None
all_actions = []

# --- ระบบ Buffer สำหรับการ Mapping ปุ่ม Combo ---
_capture_buffer = []
_last_capture_time = 0
_CAPTURE_WINDOW = 0.5  # ช่วงเวลาสะสมปุ่ม (วินาที)

MENU_MAIN = ["เพิ่มปุ่ม", "แก้ไขปุ่ม", "กลับ"]
MENU_EDIT = ["เปลี่ยนปุ่ม", "เปลี่ยน Action", "ลบการตั้งค่า", "กลับ"]
MENU_CONFIRM = ["ยกเลิก", "ยืนยัน"]
ITEMS_PER_PAGE = 6


def get_edit_items():
    if not edit_list:
        return ["(ว่าง)", "กลับ"]
    start = edit_page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items = [i["label"] for i in edit_list[start:end]]
    if start > 0:
        items.append("ก่อนหน้า")
    if end < len(edit_list):
        items.append("ถัดไป")
    items.append("กลับ")
    return items


def reset():
    global \
        state, \
        edit_list, \
        edit_page, \
        target_item, \
        pending_action, \
        new_input_val, \
        new_action_val, \
        _capture_buffer
    state = "main"
    edit_list = []
    edit_page = 0
    target_item = None
    pending_action = None
    new_input_val = None
    new_action_val = None
    _capture_buffer = []


def run(selected_item, context):
    global \
        state, \
        edit_list, \
        edit_page, \
        target_item, \
        pending_action, \
        new_action_val, \
        selected_cat, \
        all_actions
    overlay = context["overlay"]

    if state == "main":
        if selected_item == "กลับ":
            return "SWITCH:main"
        elif selected_item == "เพิ่มปุ่ม":
            pending_action = "add_new"
            return "LISTEN_INPUT"
        elif selected_item == "แก้ไขปุ่ม":
            state = "select_edit"
            edit_page = 0
            edit_list.clear()
            mapping = load_mapping()
            if mapping:
                for m_id, m_data in mapping.items():
                    if not isinstance(m_data, dict):
                        continue
                    for k, v in m_data.get("analogs", {}).items():
                        edit_list.append(
                            {
                                "label": f"แกน {v} ({k})",
                                "mod": m_id,
                                "type": "analogs",
                                "key": k,
                            }
                        )
                    for k, v in m_data.get("buttons", {}).items():
                        edit_list.append(
                            {
                                "label": f"{format_button_name(v)} ({k})",
                                "mod": m_id,
                                "type": "buttons",
                                "key": k,
                            }
                        )
            overlay.menu_items = get_edit_items()
            return "UPDATE_UI"

    elif state == "select_edit":
        if selected_item == "กลับ":
            state = "main"
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"
        elif selected_item == "ถัดไป":
            edit_page += 1
            overlay.menu_items = get_edit_items()
            return "UPDATE_UI"
        elif selected_item == "ก่อนหน้า":
            edit_page -= 1
            overlay.menu_items = get_edit_items()
            return "UPDATE_UI"
        elif selected_item != "(ว่าง)":
            target_item = next(
                (i for i in edit_list if i["label"] == selected_item), None
            )
            if target_item:
                state = "edit_action"
                overlay.menu_items = MENU_EDIT
                overlay.center_msg = f"{target_item['label']}"
                return "UPDATE_UI"

    elif state == "edit_action":
        if selected_item == "กลับ":
            state = "select_edit"
            overlay.menu_items = get_edit_items()
            return "UPDATE_UI"
        elif selected_item == "ลบการตั้งค่า":
            pending_action = "delete"
            state = "confirm"
            overlay.menu_items = MENU_CONFIRM
            overlay.center_msg = "ยืนยันลบ?"
            return "UPDATE_UI"
        elif selected_item == "เปลี่ยนปุ่ม":
            pending_action = "change_btn"
            return "LISTEN_INPUT"
        elif selected_item == "เปลี่ยน Action":
            pending_action = "change_action"
            state = "select_cat"
            all_actions = get_all_available_actions()
            overlay.menu_items = list(set([i["mod_name"] for i in all_actions])) + [
                "ยกเลิก"
            ]
            return "UPDATE_UI"

    elif state == "select_cat":
        if selected_item == "ยกเลิก":
            state = "main" if pending_action == "add_new" else "edit_action"
            overlay.menu_items = MENU_MAIN if pending_action == "add_new" else MENU_EDIT
            return "UPDATE_UI"
        else:
            selected_cat = selected_item
            state = "select_action"
            filtered = [
                i["label"] for i in all_actions if i["mod_name"] == selected_cat
            ]
            overlay.menu_items = filtered + ["กลับ"]
            return "UPDATE_UI"

    elif state == "select_action":
        if selected_item == "กลับ":
            state = "select_cat"
            overlay.menu_items = list(set([i["mod_name"] for i in all_actions])) + [
                "ยกเลิก"
            ]
            return "UPDATE_UI"
        else:
            new_action_val = next(
                (
                    i
                    for i in all_actions
                    if i["label"] == selected_item and i["mod_name"] == selected_cat
                ),
                None,
            )
            if new_action_val:
                state = "confirm"
                overlay.menu_items = MENU_CONFIRM
                overlay.center_msg = f"{new_action_val['label']}\nกดยืนยัน"
                return "UPDATE_UI"

    elif state == "confirm":
        if selected_item == "ยืนยัน":
            mapping = load_mapping()
            if pending_action == "delete" and target_item:
                m, c, k = target_item["mod"], target_item["type"], target_item["key"]
                if m in mapping and c in mapping[m] and k in mapping[m][c]:
                    del mapping[m][c][k]
            elif (
                pending_action == "change_btn"
                and new_input_val is not None
                and target_item
            ):
                m, c, k = target_item["mod"], target_item["type"], target_item["key"]
                if m not in mapping:
                    mapping[m] = {"analogs": {}, "buttons": {}}
                mapping[m][c][k] = new_input_val
            elif (
                pending_action == "add_new"
                and new_action_val
                and new_input_val is not None
            ):
                n_mod, n_cat, n_key = (
                    new_action_val["mod"],
                    new_action_val["cat"],
                    new_action_val["key"],
                )
                if n_mod not in mapping:
                    mapping[n_mod] = {"analogs": {}, "buttons": {}}
                mapping[n_mod][n_cat][n_key] = new_input_val
            elif pending_action == "change_action" and target_item and new_action_val:
                old_val = (
                    mapping.get(target_item["mod"], {})
                    .get(target_item["type"], {})
                    .get(target_item["key"])
                )
                if (
                    target_item["mod"] in mapping
                    and target_item["type"] in mapping[target_item["mod"]]
                ):
                    if (
                        target_item["key"]
                        in mapping[target_item["mod"]][target_item["type"]]
                    ):
                        del mapping[target_item["mod"]][target_item["type"]][
                            target_item["key"]
                        ]
                n_mod, n_cat, n_key = (
                    new_action_val["mod"],
                    new_action_val["cat"],
                    new_action_val["key"],
                )
                if n_mod not in mapping:
                    mapping[n_mod] = {"analogs": {}, "buttons": {}}
                mapping[n_mod][n_cat][n_key] = old_val

            save_mapping(mapping)
            reset()
            overlay.menu_items = MENU_MAIN
            overlay.center_msg = "บันทึกแล้ว!"
            return "UPDATE_UI"
        else:
            reset()
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"
    return None


# --- ฟังก์ชันสำหรับดักจับ Input แบบ Combo (แก้ไขปัญหาปล่อยปุ่มไม่พร้อมกัน) ---
def set_detected_input(val):
    global new_input_val, _capture_buffer, _last_capture_time
    now = time.time()

    # แปลง input เป็น list เสมอ
    incoming_btns = val if isinstance(val, list) else [val]

    # ถ้าห่างจากปุ่มล่าสุดเกิน 0.5 วินาที ให้ถือว่าเป็นชุดใหม่
    if now - _last_capture_time > _CAPTURE_WINDOW:
        _capture_buffer = incoming_btns
    else:
        # ถ้ายังอยู่ในช่วงเวลา ให้สะสมปุ่มเพิ่ม (Combo)
        for b in incoming_btns:
            if b not in _capture_buffer:
                _capture_buffer.append(b)

    _last_capture_time = now

    # สรุปค่า: ถ้ามีหลายปุ่มให้เก็บเป็น List ถ้ามีปุ่มเดียวให้เก็บเป็น Int
    if len(_capture_buffer) > 1:
        new_input_val = sorted(_capture_buffer, key=lambda x: str(x))
    else:
        new_input_val = _capture_buffer[0] if _capture_buffer else None


def proceed_after_input(context):
    global state, new_action_val, all_actions, selected_cat, _capture_buffer
    overlay = context["overlay"]

    if pending_action == "change_btn":
        state = "confirm"
        overlay.menu_items = MENU_CONFIRM
        name = format_button_name(new_input_val)
        overlay.center_msg = f"ค่าใหม่: {name}\nกดยืนยัน"
        _capture_buffer = []  # ล้างบัฟเฟอร์เมื่อเสร็จสิ้น
        return "UPDATE_UI"

    elif pending_action == "add_new":
        state = "select_cat"
        all_actions = get_all_available_actions()
        overlay.menu_items = list(set([i["mod_name"] for i in all_actions])) + ["ยกเลิก"]
        overlay.center_msg = "ตรวจพบแล้ว\nเลือก Action ต่อ"
        _capture_buffer = []  # ล้างบัฟเฟอร์เมื่อเสร็จสิ้น
        return "UPDATE_UI"

    return None
