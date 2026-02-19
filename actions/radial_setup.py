import json
import math
import os

import pygame

try:
    from ui.overlay_ui import RadialMenuOverlay
except ImportError:
    RadialMenuOverlay = None

ACTION_INFO = {
    "id": "radial_setup",
    "name": "ระบบตั้งค่าเมนูวงกลม",
    "actions": [{"key": "open_menu", "type": "button", "desc": "เปิด/ปิด เมนูวงกลม"}],
}

# --- State Variables ---
overlay_window = None
is_active = False
last_btn_state = False

current_state = "main"
target_edit_item = None
pending_action = None
dynamic_edit_list = []
all_actions_list = []
new_input_val = None
new_action_val = None

edit_page = 0
ITEMS_PER_PAGE = 6
selected_category = None

# ✨ ระบบป้องกันบั๊กและช่วยการรับค่า
new_input_type = "buttons"
wait_for_neutral = False
initial_axes_values = {}

MENU_MAIN = ["ตั้งค่าปุ่ม", "ความเร็วเมาส์", "ปิดเมนู"]
MENU_SETUP = ["เพิ่มปุ่ม", "แก้ไขปุ่ม", "กลับ"]
MENU_SPEEDS = ["ช้า (5)", "ปกติ (15)", "เร็ว (25)", "ติดจรวด (40)", "กลับ"]
MENU_EDIT_ACTION = ["เปลี่ยนปุ่ม", "เปลี่ยน Action", "ลบการตั้งค่า", "กลับ"]
MENU_CONFIRM = ["ยกเลิก", "ยืนยัน"]


def get_all_available_actions():
    actions = []
    actions_dir = os.path.dirname(__file__)
    for f in os.listdir(actions_dir):
        if f.endswith(".py") and f != "__init__.py":
            try:
                mod_name = f[:-3]
                m = __import__(f"actions.{mod_name}", fromlist=[""])
                if hasattr(m, "ACTION_INFO"):
                    info = m.ACTION_INFO
                    cat_name = info.get("name", info["id"])
                    for act in info.get("actions", []):
                        cat = "analogs" if act.get("type") == "analog" else "buttons"
                        actions.append(
                            {
                                "label": act["desc"],
                                "mod": info["id"],
                                "mod_name": cat_name,
                                "cat": cat,
                                "key": act["key"],
                            }
                        )
            except:
                pass
    return actions


def get_edit_page_items():
    if not dynamic_edit_list:
        return ["(ว่าง)", "กลับ"]
    start = edit_page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items = [i["label"] for i in dynamic_edit_list[start:end]]
    if start > 0:
        items.append("ก่อนหน้า")
    if end < len(dynamic_edit_list):
        items.append("ถัดไป")
    items.append("กลับ")
    return items


def run(ui_virtual, joystick, app_config, mod_mapping):
    global overlay_window, is_active, last_btn_state
    global current_state, target_edit_item, pending_action
    global dynamic_edit_list, all_actions_list, new_input_val, new_action_val
    global \
        edit_page, \
        selected_category, \
        new_input_type, \
        wait_for_neutral, \
        initial_axes_values

    trigger_btn = mod_mapping.get("buttons", {}).get("open_menu")
    if trigger_btn is None:
        return False

    btn_pressed = joystick.get_button(trigger_btn)

    if btn_pressed and not last_btn_state:
        is_active = not is_active
        if is_active and RadialMenuOverlay:
            current_state = "main"
            overlay_window = RadialMenuOverlay(menu_items=MENU_MAIN)
            overlay_window.show()
        elif overlay_window:
            overlay_window.close()
            overlay_window = None
            last_btn_state = btn_pressed
            return "RELOAD"

    last_btn_state = btn_pressed

    if is_active and overlay_window:
        # --- 🛠️ โหมดดักจับสัญญาณ (Input Listener) ---
        if current_state == "listen_input":
            if not initial_axes_values:
                for a in range(joystick.get_numaxes()):
                    initial_axes_values[a] = joystick.get_axis(a)

            if wait_for_neutral:
                if not joystick.get_button(0):
                    wait_for_neutral = False
                return True

            input_detected = False
            # เช็คปุ่ม
            for i in range(joystick.get_numbuttons()):
                if joystick.get_button(i) and i != trigger_btn:
                    new_input_val = i
                    new_input_type = "buttons"
                    input_detected = True
                    break
            # เช็คแกน (Delta Check)
            if not input_detected:
                for j in range(joystick.get_numaxes()):
                    if abs(joystick.get_axis(j) - initial_axes_values.get(j, 0)) > 0.7:
                        new_input_val = j
                        new_input_type = "analogs"
                        input_detected = True
                        break

            if input_detected:
                initial_axes_values = {}
                inp_name = (
                    f"แกน {new_input_val}"
                    if new_input_type == "analogs"
                    else f"ปุ่ม {new_input_val}"
                )
                overlay_window.center_msg = f"{inp_name}\nตรวจพบสัญญาณแล้ว"
                if pending_action == "change_btn":
                    current_state = "confirm"
                    overlay_window.menu_items = MENU_CONFIRM
                    overlay_window.center_msg = f"{inp_name}\nกดยืนยันเพื่อเปลี่ยน"
                elif pending_action == "add_new_btn":
                    current_state = "select_action_category"
                    all_actions_list = get_all_available_actions()
                    cats = list(set([i["mod_name"] for i in all_actions_list]))
                    overlay_window.menu_items = cats + ["ยกเลิก"]
                    overlay_window.center_msg = f"{inp_name}\nโปรดเลือกหมวดหมู่"
                overlay_window.update()
                pygame.time.wait(400)
                return True
            return True

        # --- ระบบเมนูปกติ ---
        axis_x, axis_y = joystick.get_axis(0), joystick.get_axis(1)
        if math.sqrt(axis_x**2 + axis_y**2) > 0.4:
            angle = (math.degrees(math.atan2(axis_y, axis_x)) + 90) % 360
            overlay_window.update_selection(angle)

        if joystick.get_button(0):
            selected_item = overlay_window.menu_items[overlay_window.current_selection]

            if current_state == "main":
                if selected_item == "ปิดเมนู":
                    is_active = False
                    overlay_window.close()
                    overlay_window = None
                    return "RELOAD"
                elif selected_item == "ตั้งค่าปุ่ม":
                    current_state = "setup_type"
                    overlay_window.menu_items = MENU_SETUP
                elif selected_item == "ความเร็วเมาส์":
                    current_state = "adjust_speed"
                    overlay_window.menu_items = MENU_SPEEDS

            elif current_state == "adjust_speed":
                if selected_item == "กลับ":
                    current_state = "main"
                    overlay_window.menu_items = MENU_MAIN
                else:
                    speed = int(selected_item.split("(")[1].split(")")[0])
                    app_config["mouse"]["speed_x"] = speed
                    app_config["mouse"]["speed_y"] = speed
                    current_state = "confirm"
                    pending_action = "save_config"
                    overlay_window.menu_items = MENU_CONFIRM
                    overlay_window.center_msg = f"ความเร็ว: {speed}\nกดยืนยันเพื่อบันทึก"

            elif current_state == "setup_type":
                if selected_item == "กลับ":
                    current_state = "main"
                    overlay_window.menu_items = MENU_MAIN
                elif selected_item == "เพิ่มปุ่ม":
                    pending_action = "add_new_btn"
                    current_state = "listen_input"
                    wait_for_neutral = True
                    initial_axes_values = {}
                    overlay_window.menu_items = ["(โปรดกดปุ่ม/โยกแกน)"]
                    overlay_window.center_msg = "รอรับสัญญาณ...\n(โปรดปล่อยมือและกดใหม่)"
                elif selected_item == "แก้ไขปุ่ม":
                    current_state = "edit_select"
                    edit_page = 0
                    mapping_path = os.path.join("config", "mapping.json")
                    dynamic_edit_list.clear()
                    if os.path.exists(mapping_path):
                        with open(mapping_path, "r", encoding="utf-8") as f:
                            full_map = json.load(f)
                            for m_id, m_data in full_map.items():
                                for k, v in m_data.get("analogs", {}).items():
                                    dynamic_edit_list.append(
                                        {
                                            "label": f"แกน {v} ({k})",
                                            "mod": m_id,
                                            "type": "analogs",
                                            "key": k,
                                        }
                                    )
                                for k, v in m_data.get("buttons", {}).items():
                                    dynamic_edit_list.append(
                                        {
                                            "label": f"ปุ่ม {v} ({k})",
                                            "mod": m_id,
                                            "type": "buttons",
                                            "key": k,
                                        }
                                    )
                    overlay_window.menu_items = get_edit_page_items()

            elif current_state == "edit_select":
                if selected_item == "กลับ":
                    current_state = "setup_type"
                    overlay_window.menu_items = MENU_SETUP
                elif selected_item == "ถัดไป":
                    edit_page += 1
                    overlay_window.menu_items = get_edit_page_items()
                elif selected_item == "ก่อนหน้า":
                    edit_page -= 1
                    overlay_window.menu_items = get_edit_page_items()
                elif selected_item != "(ว่าง)":
                    target_edit_item = next(
                        (i for i in dynamic_edit_list if i["label"] == selected_item),
                        None,
                    )
                    if target_edit_item:
                        current_state = "edit_action"
                        overlay_window.menu_items = MENU_EDIT_ACTION
                        overlay_window.center_msg = (
                            f"{target_edit_item['label']}\nเลือกคำสั่งที่จะทำ"
                        )

            elif current_state == "edit_action":
                if selected_item == "กลับ":
                    current_state = "edit_select"
                    overlay_window.menu_items = get_edit_page_items()
                    overlay_window.center_msg = ""
                elif selected_item == "ลบการตั้งค่า":
                    pending_action = "delete"
                    current_state = "confirm"
                    overlay_window.menu_items = MENU_CONFIRM
                    overlay_window.center_msg = (
                        f"ยืนยันการลบ?\n{target_edit_item['label']}"
                    )
                elif selected_item == "เปลี่ยนปุ่ม":
                    pending_action = "change_btn"
                    current_state = "listen_input"
                    wait_for_neutral = True
                    overlay_window.menu_items = ["(โปรดกดปุ่ม/โยกแกน)"]
                    overlay_window.center_msg = "รอรับสัญญาณใหม่..."
                elif selected_item == "เปลี่ยน Action":
                    pending_action = "change_action"
                    current_state = "select_action_category"
                    all_actions_list = get_all_available_actions()
                    cats = list(set([i["mod_name"] for i in all_actions_list]))
                    overlay_window.menu_items = cats + ["ยกเลิก"]
                    overlay_window.center_msg = "หน้าที่ใหม่\nโปรดเลือกหมวดหมู่"

            elif current_state == "select_action_category":
                if selected_item == "ยกเลิก":
                    current_state = "edit_action"
                    overlay_window.menu_items = MENU_EDIT_ACTION
                else:
                    selected_category = selected_item
                    current_state = "select_new_action"
                    filtered = [
                        i["label"]
                        for i in all_actions_list
                        if i["mod_name"] == selected_category
                    ]
                    overlay_window.menu_items = filtered + ["กลับ"]
                    overlay_window.center_msg = f"หมวด: {selected_category}\nเลือกหน้าที่"

            elif current_state == "select_new_action":
                if selected_item == "กลับ":
                    current_state = "select_action_category"
                    overlay_window.menu_items = list(
                        set([i["mod_name"] for i in all_actions_list])
                    ) + ["ยกเลิก"]
                else:
                    new_action_val = next(
                        (
                            i
                            for i in all_actions_list
                            if i["label"] == selected_item
                            and i["mod_name"] == selected_category
                        ),
                        None,
                    )
                    current_state = "confirm"
                    overlay_window.menu_items = MENU_CONFIRM
                    overlay_window.center_msg = (
                        f"{new_action_val['label']}\nกดยืนยันเพื่อบันทึก"
                    )

            elif current_state == "confirm":
                if selected_item == "ยืนยัน":
                    mapping_path = os.path.join("config", "mapping.json")
                    config_path = os.path.join("config", "config.json")

                    if pending_action == "save_config":  # บันทึกความเร็วเมาส์
                        with open(config_path, "w", encoding="utf-8") as f:
                            json.dump(app_config, f, indent=4, ensure_ascii=False)
                    else:  # บันทึกการ Mapping ปุ่ม
                        with open(mapping_path, "r", encoding="utf-8") as f:
                            full_map = json.load(f)
                        if pending_action == "add_new_btn":
                            n_mod, n_cat, n_key = (
                                new_action_val["mod"],
                                new_action_val["cat"],
                                new_action_val["key"],
                            )
                            if n_mod not in full_map:
                                full_map[n_mod] = {"analogs": {}, "buttons": {}}
                            full_map[n_mod][n_cat][n_key] = new_input_val
                        elif pending_action == "delete":
                            m, c, k = (
                                target_edit_item["mod"],
                                target_edit_item["type"],
                                target_edit_item["key"],
                            )
                            if k in full_map.get(m, {}).get(c, {}):
                                del full_map[m][c][k]
                        elif pending_action == "change_btn":
                            m, c, k = (
                                target_edit_item["mod"],
                                target_edit_item["type"],
                                target_edit_item["key"],
                            )
                            full_map[m][c][k] = new_input_val
                        elif pending_action == "change_action":
                            old_val = full_map[target_edit_item["mod"]][
                                target_edit_item["type"]
                            ][target_edit_item["key"]]
                            del full_map[target_edit_item["mod"]][
                                target_edit_item["type"]
                            ][target_edit_item["key"]]
                            n_mod, n_cat, n_key = (
                                new_action_val["mod"],
                                new_action_val["cat"],
                                new_action_val["key"],
                            )
                            if n_mod not in full_map:
                                full_map[n_mod] = {"analogs": {}, "buttons": {}}
                            full_map[n_mod][n_cat][n_key] = old_val
                        with open(mapping_path, "w", encoding="utf-8") as f:
                            json.dump(full_map, f, indent=4, ensure_ascii=False)

                    current_state = "main"
                    overlay_window.menu_items = MENU_MAIN
                    overlay_window.center_msg = ""
                else:
                    current_state = "main"
                    overlay_window.menu_items = MENU_MAIN
                    overlay_window.center_msg = ""

            if overlay_window:
                overlay_window.update()
            pygame.time.wait(250)
        return True
    return False
