import pygame

from menus.utils import get_all_available_actions, get_emoji, load_recipes, save_recipes

state = "main"
recipes = []
page = 0
target_recipe = None
temp_seq = []
is_recording = False
pending_action = None
new_action_val = None
selected_cat = None
all_actions = []

MENU_MAIN = ["เพิ่มสูตรใหม่", "แก้ไข/ลบสูตร", "กลับ"]
MENU_RECORD = ["บันทึกสูตร", "ยกเลิก"]
MENU_EDIT = ["เปลี่ยน Action", "ลบสูตร", "กลับ"]
MENU_CONFIRM = ["ยกเลีก", "ยืนยัน"]  # Fix Typo คำว่า ยกเลิก
ITEMS_PER_PAGE = 6


def get_recipe_items():
    if not recipes:
        return ["(ไม่มีสูตร)", "กลับ"]
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items = [i["name"] for i in recipes[start:end]]
    if start > 0:
        items.append("ก่อนหน้า")
    if end < len(recipes):
        items.append("ถัดไป")
    items.append("กลับ")
    return items


def reset():
    global state, recipes, page, target_recipe, temp_seq, is_recording, pending_action
    state = "main"
    recipes = []
    page = 0
    target_recipe = None
    temp_seq = []
    is_recording = False
    pending_action = None


def run(selected_item, context):
    global \
        state, \
        recipes, \
        page, \
        target_recipe, \
        temp_seq, \
        is_recording, \
        pending_action, \
        new_action_val, \
        selected_cat, \
        all_actions
    overlay = context["overlay"]

    if state == "main":
        if selected_item == "กลับ":
            return "SWITCH:main"
        elif selected_item == "เพิ่มสูตรใหม่":
            temp_seq = []
            is_recording = True
            state = "recording"
            overlay.menu_items = MENU_RECORD
            overlay.center_msg = "กดปุ่มเพิ่มสูตร..."
            return "START_SEQUENCE_LISTEN"
        elif selected_item == "แก้ไข/ลบสูตร":
            state = "select_list"
            recipes = load_recipes()
            page = 0
            overlay.menu_items = get_recipe_items()
            return "UPDATE_UI"

    elif state == "recording":
        if selected_item == "ยกเลิก":
            reset()
            overlay.menu_items = MENU_MAIN
            overlay.center_msg = ""
            return "STOP_SEQUENCE_LISTEN"
        elif selected_item == "บันทึกสูตร":
            if len(temp_seq) > 0:
                pending_action = "save_new"
                state = "select_cat"
                all_actions = get_all_available_actions()

                # ✨ Fix: Handle Empty Actions
                if not all_actions:
                    overlay.center_msg = "Error: ไม่พบ Action\n(ตรวจสอบ Path)"
                    state = "recording"
                    return "UPDATE_UI"

                cats = list(set([i["mod_name"] for i in all_actions]))
                overlay.menu_items = cats + ["ยกเลิก"]
                emoji = "".join([get_emoji(x) for x in temp_seq])
                overlay.center_msg = f"สูตร: {emoji}"
                return "STOP_SEQUENCE_LISTEN"
            else:
                overlay.center_msg = "ไม่มีปุ่มในสูตร"
                return "UPDATE_UI"

    elif state == "select_list":
        if selected_item == "กลับ":
            state = "main"
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"
        elif selected_item == "ถัดไป":
            page += 1
            overlay.menu_items = get_recipe_items()
            return "UPDATE_UI"
        elif selected_item == "ก่อนหน้า":
            page -= 1
            overlay.menu_items = get_recipe_items()
            return "UPDATE_UI"
        elif selected_item != "(ไม่มีสูตร)":
            target_recipe = next(
                (r for r in recipes if r["name"] == selected_item), None
            )
            if target_recipe:
                state = "edit_opts"
                overlay.menu_items = MENU_EDIT
                seq = target_recipe.get("sequence", [])
                emoji = "".join([get_emoji(x) for x in seq])
                overlay.center_msg = f"สูตร: {emoji}"
                return "UPDATE_UI"

    elif state == "edit_opts":
        if selected_item == "กลับ":
            state = "select_list"
            overlay.menu_items = get_recipe_items()
            return "UPDATE_UI"
        elif selected_item == "ลบสูตร":
            pending_action = "delete"
            state = "confirm"
            overlay.menu_items = MENU_CONFIRM
            overlay.center_msg = "ยืนยันลบ?"
            return "UPDATE_UI"
        elif selected_item == "เปลี่ยน Action":
            pending_action = "change_action"
            state = "select_cat"
            all_actions = get_all_available_actions()

            # ✨ Fix: Handle Empty Actions
            if not all_actions:
                overlay.center_msg = "Error: ไม่พบ Action\n(ตรวจสอบ Path)"
                state = "edit_opts"
                return "UPDATE_UI"

            overlay.menu_items = list(set([i["mod_name"] for i in all_actions])) + [
                "ยกเลิก"
            ]
            return "UPDATE_UI"

    elif state == "select_cat":
        if selected_item == "ยกเลิก":
            # ✨ Fix: Correct Back Logic
            if pending_action == "save_new":
                # ถ้าเพิ่มสูตรใหม่แล้วกดยกเลิกตอนเลือก Category -> กลับไปหน้า recording?
                # หรือกลับไป main? สำหรับตอนนี้ให้กลับ edit_opts หรือ main
                reset()
                overlay.menu_items = MENU_MAIN
                return "STOP_SEQUENCE_LISTEN"  # ออกจากโหมดฟัง
            else:
                state = "edit_opts"
                overlay.menu_items = MENU_EDIT
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
                (i for i in all_actions if i["label"] == selected_item), None
            )
            if new_action_val:
                state = "confirm"
                overlay.menu_items = MENU_CONFIRM
                overlay.center_msg = f"{new_action_val['label']}\nกดยืนยัน"
                return "UPDATE_UI"

    elif state == "confirm":
        if selected_item == "ยืนยัน":
            if pending_action == "delete" and target_recipe:
                recipes = load_recipes()
                new_list = [r for r in recipes if r != target_recipe]
                save_recipes(new_list)
            elif pending_action == "save_new":
                recipes = load_recipes()
                emoji = "".join([get_emoji(x) for x in temp_seq])
                recipes.append(
                    {
                        "name": f"สูตร {len(recipes) + 1}: {emoji}",
                        "sequence": temp_seq,
                        "action": new_action_val,
                    }
                )
                save_recipes(recipes)
            elif pending_action == "change_action" and target_recipe and new_action_val:
                recipes = load_recipes()
                for i, r in enumerate(recipes):
                    if r == target_recipe:
                        recipes[i]["action"] = new_action_val
                        break
                save_recipes(recipes)
            reset()
            overlay.menu_items = MENU_MAIN
            overlay.center_msg = "บันทึกแล้ว!"
            return "UPDATE_UI"
        else:
            # ✨ Fix: Cancel Logic
            reset()
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"
    return None


def toggle_recording(context):
    global is_recording
    overlay = context["overlay"]
    if state == "recording":
        is_recording = not is_recording
        if is_recording:
            overlay.center_msg = "กำลังบันทึก..."
        else:
            overlay.center_msg = "หยุดบันทึก"
        return True
    return False


def add_sequence_input(input_val, context):
    global temp_seq
    overlay = context["overlay"]
    if is_recording:
        temp_seq.append(input_val)
        emoji = "".join([get_emoji(x) for x in temp_seq])
        if len(emoji) > 15:
            emoji = "..." + emoji[-12:]
        overlay.center_msg = f"บันทึก:\n{emoji}"
        return True
    return False
