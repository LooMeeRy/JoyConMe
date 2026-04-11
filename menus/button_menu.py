# menus/button_main.py
import time

from menus.utils import (
    format_button_name,
    get_all_available_actions,
    load_mapping,
    save_mapping,
)

MENU_NAME = "ตั้งค่าปุ่ม"
MENU_TARGET = "button_main"

# --- State Management ---
state = "main"
edit_list = []
edit_page = 0
target_item = None
pending_action = None
new_input_val = None
new_action_val = None
all_actions = []

MENU_MAIN = ["เพิ่มการตั้งค่าใหม่", "รายการที่ตั้งไว้", "กลับ"]
MENU_EDIT_OPTS = ["เปลี่ยนปุ่มจอย", "ลบการตั้งค่า", "กลับ"]
MENU_CONFIRM = ["ยกเลิก", "ยืนยัน"]
ITEMS_PER_PAGE = 6


def reset():
    global \
        state, \
        edit_list, \
        edit_page, \
        target_item, \
        pending_action, \
        new_input_val, \
        new_action_val
    state = "main"
    edit_list = []
    edit_page = 0
    target_item = None
    pending_action = None
    new_input_val = None
    new_action_val = None


def get_edit_items():
    if not edit_list:
        return ["(ไม่มีข้อมูล)", "กลับ"]
    start = edit_page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items = [i["label"] for i in edit_list[start:end]]
    if start > 0:
        items.append("⬅️ ก่อนหน้า")
    if end < len(edit_list):
        items.append("ถัดไป ➡️")
    items.append("กลับ")
    return items


def run(selected_item, context):
    global \
        state, \
        edit_list, \
        edit_page, \
        target_item, \
        pending_action, \
        new_action_val, \
        all_actions, \
        new_input_val
    overlay = context["overlay"]

    full_mapping = load_mapping()
    active_prof = full_mapping.get("active_profile", "default")
    mapping = full_mapping.get("profiles", {}).get(active_prof, {})

    # --- 1. หน้าหลัก ---
    if state == "main":
        if selected_item == "กลับ":
            return "SWITCH:main"
        elif selected_item == "เพิ่มการตั้งค่าใหม่":
            state = "select_cat"
            all_actions = get_all_available_actions()
            overlay.menu_items = sorted(
                list(set([i["mod_name"] for i in all_actions]))
            ) + ["ยกเลิก"]
            return "UPDATE_UI"
        elif selected_item == "รายการที่ตั้งไว้":
            state = "select_edit"
            edit_list = []
            for m_id, categories in mapping.items():
                for cat_id, keys in categories.items():
                    for k, v in keys.items():
                        if m_id == "macro_keyboard":
                            label = f"📜 {v} (ปุ่ม {k})"
                        else:
                            label = f"🎮 {k} ({format_button_name(v)})"
                        edit_list.append(
                            {
                                "label": label,
                                "mod": m_id,
                                "cat": cat_id,
                                "key": k,
                                "val": v,
                            }
                        )
            overlay.menu_items = get_edit_items()
            return "UPDATE_UI"

    # --- 2. เลือกหมวดหมู่ ---
    elif state == "select_cat":
        if selected_item == "ยกเลิก":
            reset()
            overlay.menu_items = MENU_MAIN
        else:
            state = "select_action"
            filtered = [i for i in all_actions if i["mod_name"] == selected_item]
            overlay.menu_items = [i["label"] for i in filtered] + ["กลับ"]
            context["temp_actions"] = filtered
        return "UPDATE_UI"

    # --- 3. เลือก Action ---
    elif state == "select_action":
        if selected_item == "กลับ":
            state = "main"
            overlay.menu_items = MENU_MAIN
        else:
            all_actions = get_all_available_actions()
            new_action_val = next(
                (i for i in all_actions if i["label"] == selected_item), None
            )
            if new_action_val:
                pending_action = "add_new"
                overlay.center_msg = f"ตั้งค่า: {selected_item}\nกดปุ่มหรือโยกแกน..."
                return "LISTEN_INPUT"
        return "UPDATE_UI"

    # --- 4. แก้ไขรายการเดิม ---
    elif state == "select_edit":
        if selected_item == "กลับ":
            reset()
            overlay.menu_items = MENU_MAIN
        elif selected_item == "ถัดไป ➡️":
            edit_page += 1
            overlay.menu_items = get_edit_items()
        elif selected_item == "⬅️ ก่อนหน้า":
            edit_page -= 1
            overlay.menu_items = get_edit_items()
        elif selected_item != "(ไม่มีข้อมูล)":
            target_item = next(
                (i for i in edit_list if i["label"] == selected_item), None
            )
            if target_item:
                state = "edit_opts"
                overlay.menu_items = MENU_EDIT_OPTS
                overlay.center_msg = f"แก้ไข: {target_item['label']}"
        return "UPDATE_UI"

    elif state == "edit_opts":
        if selected_item == "กลับ":
            state = "select_edit"
            overlay.menu_items = get_edit_items()
        elif selected_item == "ลบการตั้งค่า":
            pending_action = "delete"
            state = "confirm"
            overlay.menu_items = MENU_CONFIRM
            overlay.center_msg = "ยืนยันการลบ?"
        elif selected_item == "เปลี่ยนปุ่มจอย":
            pending_action = "change_btn"
            return "LISTEN_INPUT"
        return "UPDATE_UI"

    # --- 5. ยืนยันและบันทึกลง JSON ---
    elif state == "confirm":
        if selected_item == "ยืนยัน":
            m_id = (
                new_action_val["mod"]
                if pending_action == "add_new"
                else target_item["mod"]
            )
            cat = (
                new_action_val["cat"]
                if pending_action == "add_new"
                else target_item["cat"]
            )

            if "profiles" not in full_mapping:
                full_mapping["profiles"] = {}
            if active_prof not in full_mapping["profiles"]:
                full_mapping["profiles"][active_prof] = {}
            mapping = full_mapping["profiles"][active_prof]

            if m_id not in mapping:
                mapping[m_id] = {"buttons": {}, "analogs": {}}

            if pending_action == "delete":
                if target_item["key"] in mapping[m_id][cat]:
                    del mapping[m_id][cat][target_item["key"]]
            else:
                # การลบของเก่าทิ้งเมื่อใช้ "เปลี่ยนปุ่มจอย"
                if pending_action == "change_btn":
                    if m_id == "macro_keyboard":
                        old_joy_key = target_item["key"]
                        if old_joy_key in mapping[m_id][cat]:
                            del mapping[m_id][cat][old_joy_key]

                # จัดรูปแบบ JSON ให้เป๊ะ
                final_val = new_input_val
                if cat == "analogs":
                    if isinstance(new_input_val, dict) and "axis" in new_input_val:
                        final_val = new_input_val["axis"]
                    elif isinstance(new_input_val, list) and len(new_input_val) > 0:
                        first = new_input_val[0]
                        if isinstance(first, dict) and "axis" in first:
                            final_val = first["axis"]
                        else:
                            final_val = first

                # บันทึก
                if m_id == "macro_keyboard":
                    joy_key = str(final_val).replace("'", '"')
                    macro_name = (
                        new_action_val["key"]
                        if pending_action == "add_new"
                        else target_item["val"]
                    )
                    mapping[m_id][cat][joy_key] = macro_name
                else:
                    act_key = (
                        new_action_val["key"]
                        if pending_action == "add_new"
                        else target_item["key"]
                    )
                    mapping[m_id][cat][act_key] = final_val

            save_mapping(full_mapping)

            # ✨ สร้างรายการ Edit List ใหม่ เพื่อให้โชว์ปุ่มอัปเดตล่าสุด
            edit_list.clear()
            for m, categories in mapping.items():
                for c_id, keys in categories.items():
                    for k, v in keys.items():
                        if m == "macro_keyboard":
                            label = f"📜 {v} (ปุ่ม {k})"
                        else:
                            label = f"🎮 {k} ({format_button_name(v)})"
                        edit_list.append(
                            {"label": label, "mod": m, "cat": c_id, "key": k, "val": v}
                        )

            # ✨ พากลับไปที่หน้า "รายการที่ตั้งไว้" ทันที ไม่ต้องกลับไปหน้าแรก
            state = "select_edit"
            overlay.menu_items = get_edit_items()
            overlay.center_msg = "บันทึกสำเร็จ!"

            # ล้างเฉพาะตัวแปรชั่วคราวทิ้ง (ไม่ทำลาย state หน้าปัจจุบัน)
            target_item = None
            pending_action = None
            new_input_val = None
            new_action_val = None

            return "SAVE_MAPPING"

        else:
            # ✨ ถ้ายกเลิก ให้ถอยกลับ 1 สเต็ปอย่างฉลาด
            if pending_action == "add_new":
                state = "main"
                overlay.menu_items = MENU_MAIN
            else:
                state = "edit_opts"
                overlay.menu_items = MENU_EDIT_OPTS
                overlay.center_msg = f"แก้ไข: {target_item['label']}"

            pending_action = None
            new_input_val = None
            return "UPDATE_UI"

    return None


def set_detected_input(val):
    global new_input_val
    if isinstance(val, list):
        if len(val) == 1:
            new_input_val = val[0]
        elif len(val) > 1:
            new_input_val = val
        else:
            new_input_val = None
    else:
        new_input_val = val


def proceed_after_input(context):
    global state, new_input_val
    overlay = context["overlay"]
    state = "confirm"
    overlay.menu_items = MENU_CONFIRM

    from menus.utils import format_button_name

    display_name = format_button_name(new_input_val)

    overlay.center_msg = f"จับสัญญาณ: {display_name}\nยืนยันเพื่อบันทึก"
    return "UPDATE_UI"
