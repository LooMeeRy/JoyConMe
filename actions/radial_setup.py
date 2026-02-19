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
initial_axes_values = {}  # เก็บค่าเริ่มต้นของแกนจอยเพื่อป้องกันการลั่นเอง

MENU_MAIN = ["ตั้งค่าปุ่ม", "ความเร็วเมาส์", "ปิดเมนู"]
MENU_SETUP = ["เพิ่มปุ่ม", "แก้ไขปุ่ม", "กลับ"]
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


def get_categories():
    cats = []
    for act in all_actions_list:
        if act["mod_name"] not in cats:
            cats.append(act["mod_name"])
    return cats


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
        # ---------------------------------------------------------
        # 🛠️ โหมดดักจับสัญญาณ (Input Listener)
        # ---------------------------------------------------------
        if current_state == "listen_input":
            # 1. จำค่าเริ่มต้นของแกนจอย (ป้องกันบั๊ก L2/R2 ลั่นเอง)
            if not initial_axes_values:
                for a in range(joystick.get_numaxes()):
                    initial_axes_values[a] = joystick.get_axis(a)

            # 2. ระบบแก้ค้าง: รอให้ปล่อยปุ่มยืนยัน (A) ก่อน
            if wait_for_neutral:
                if not joystick.get_button(0):
                    wait_for_neutral = False
                return True

            input_detected = False
            # 3. เช็คปุ่มกด
            for i in range(joystick.get_numbuttons()):
                if joystick.get_button(i) and i != trigger_btn:
                    new_input_val = i
                    new_input_type = "buttons"
                    input_detected = True
                    break

            # 4. เช็คแกนอนาล็อก (เช็คการขยับจริงจากจุดเริ่มต้น)
            if not input_detected:
                for j in range(joystick.get_numaxes()):
                    current_val = joystick.get_axis(j)
                    start_val = initial_axes_values.get(j, 0)
                    if abs(current_val - start_val) > 0.7:
                        new_input_val = j
                        new_input_type = "analogs"
                        input_detected = True
                        break

            if input_detected:
                initial_axes_values = {}  # เคลียร์ค่าทิ้ง
                inp_name = (
                    f"แกน {new_input_val}"
                    if new_input_type == "analogs"
                    else f"ปุ่ม {new_input_val}"
                )

                if pending_action == "change_btn":
                    current_state = "confirm"
                    overlay_window.menu_items = MENU_CONFIRM
                    overlay_window.center_msg = f"{inp_name}\nยืนยันการเปลี่ยน?"
                elif pending_action == "add_new_btn":
                    current_state = "select_action_category"
                    all_actions_list = get_all_available_actions()
                    overlay_window.menu_items = get_categories() + ["ยกเลิก"]
                    overlay_window.center_msg = f"{inp_name}\nโปรดเลือกหมวดหมู่"

                overlay_window.update()
                pygame.time.wait(400)
                return True
            return True

        # --- ระบบเลือกเมนูปกติ ---
        axis_x = joystick.get_axis(0)
        axis_y = joystick.get_axis(1)
        strength = math.sqrt(axis_x**2 + axis_y**2)

        if strength > 0.4:
            radians = math.atan2(axis_y, axis_x)
            angle = (math.degrees(radians) + 90) % 360
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
                    mapping_path = os.path.join(
                        os.path.dirname(__file__), "..", "config", "mapping.json"
                    )
                    dynamic_edit_list.clear()
                    if os.path.exists(mapping_path):
                        with open(mapping_path, "r", encoding="utf-8") as f:
                            full_map = json.load(f)
                            for mod_id, mod_data in full_map.items():
                                for act_key, hw_id in mod_data.get(
                                    "analogs", {}
                                ).items():
                                    dynamic_edit_list.append(
                                        {
                                            "label": f"แกน {hw_id} ({act_key})",
                                            "mod": mod_id,
                                            "type": "analogs",
                                            "key": act_key,
                                        }
                                    )
                                for act_key, hw_id in mod_data.get(
                                    "buttons", {}
                                ).items():
                                    dynamic_edit_list.append(
                                        {
                                            "label": f"ปุ่ม {hw_id} ({act_key})",
                                            "mod": mod_id,
                                            "type": "buttons",
                                            "key": act_key,
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
                            f"{target_edit_item['label']}\nเลือกการกระทำ"
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
                    initial_axes_values = {}
                    overlay_window.menu_items = ["(โปรดกดปุ่ม/โยกแกน)"]
                    overlay_window.center_msg = "รอรับสัญญาณ...\n(โปรดปล่อยมือและกดใหม่)"
                elif selected_item == "เปลี่ยน Action":
                    pending_action = "change_action"
                    current_state = "select_action_category"
                    all_actions_list = get_all_available_actions()
                    overlay_window.menu_items = get_categories() + ["ยกเลิก"]
                    overlay_window.center_msg = "เปลี่ยนหน้าที่\nเลือกหมวดหมู่"

            elif current_state == "select_action_category":
                if selected_item == "ยกเลิก":
                    if pending_action == "add_new_btn":
                        current_state = "setup_type"
                        overlay_window.menu_items = MENU_SETUP
                    else:
                        current_state = "edit_action"
                        overlay_window.menu_items = MENU_EDIT_ACTION
                    overlay_window.center_msg = ""
                else:
                    selected_category = selected_item
                    current_state = "select_new_action"
                    filtered_actions = [
                        i["label"]
                        for i in all_actions_list
                        if i["mod_name"] == selected_category
                    ]
                    overlay_window.menu_items = filtered_actions + ["กลับ"]
                    overlay_window.center_msg = (
                        f"หมวด: {selected_category}\nเลือกหน้าที่ใหม่"
                    )

            elif current_state == "select_new_action":
                if selected_item == "กลับ":
                    current_state = "select_action_category"
                    overlay_window.menu_items = get_categories() + ["ยกเลิก"]
                    overlay_window.center_msg = "เลือกหมวดหมู่"
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
                    if new_action_val:
                        current_state = "confirm"
                        overlay_window.menu_items = MENU_CONFIRM
                        inp_name = (
                            f"แกน {new_input_val}"
                            if new_input_type == "analogs"
                            else f"ปุ่ม {new_input_val}"
                        )
                        overlay_window.center_msg = (
                            f"{new_action_val['label']}\nยืนยันค่าสำหรับ {inp_name}?"
                        )

            elif current_state == "confirm":
                if selected_item == "ยกเลิก":
                    if pending_action == "add_new_btn":
                        current_state = "select_new_action"
                        filtered = [
                            i["label"]
                            for i in all_actions_list
                            if i["mod_name"] == selected_category
                        ]
                        overlay_window.menu_items = filtered + ["กลับ"]
                    else:
                        current_state = "edit_action"
                        overlay_window.menu_items = MENU_EDIT_ACTION
                    overlay_window.center_msg = ""
                elif selected_item == "ยืนยัน":
                    mapping_path = os.path.join(
                        os.path.dirname(__file__), "..", "config", "mapping.json"
                    )
                    with open(mapping_path, "r", encoding="utf-8") as f:
                        full_map = json.load(f)
                    if (
                        pending_action == "add_new_btn"
                        and new_action_val
                        and new_input_val is not None
                    ):
                        n_mod, n_cat, n_key = (
                            new_action_val["mod"],
                            new_action_val["cat"],
                            new_action_val["key"],
                        )
                        if n_mod not in full_map:
                            full_map[n_mod] = {"analogs": {}, "buttons": {}}
                        if n_cat not in full_map[n_mod]:
                            full_map[n_mod][n_cat] = {}
                        full_map[n_mod][n_cat][n_key] = new_input_val
                    elif target_edit_item:
                        mod, cat, key = (
                            target_edit_item["mod"],
                            target_edit_item["type"],
                            target_edit_item["key"],
                        )
                        if pending_action == "delete":
                            if key in full_map.get(mod, {}).get(cat, {}):
                                del full_map[mod][cat][key]
                        elif (
                            pending_action == "change_btn" and new_input_val is not None
                        ):
                            full_map[mod][cat][key] = new_input_val
                        elif pending_action == "change_action" and new_action_val:
                            old_hw_id = full_map[mod][cat][key]
                            del full_map[mod][cat][key]
                            n_mod, n_cat, n_key = (
                                new_action_val["mod"],
                                new_action_val["cat"],
                                new_action_val["key"],
                            )
                            if n_mod not in full_map:
                                full_map[n_mod] = {"analogs": {}, "buttons": {}}
                            if n_cat not in full_map[n_mod]:
                                full_map[n_mod][n_cat] = {}
                            full_map[n_mod][n_cat][n_key] = old_hw_id
                    with open(mapping_path, "w", encoding="utf-8") as f:
                        json.dump(full_map, f, indent=4, ensure_ascii=False)
                    current_state = "main"
                    overlay_window.menu_items = MENU_MAIN
                    overlay_window.center_msg = ""
            if overlay_window:
                overlay_window.update()
            pygame.time.wait(250)
        return True
    return False
