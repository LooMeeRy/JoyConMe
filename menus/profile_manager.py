# menus/profile_manager.py
import time

from menus.utils import load_mapping, save_mapping

# ✨ ระบบ Plug & Play
MENU_NAME = "จัดการโปรไฟล์"
MENU_TARGET = "profile_manager"

# --- State ---
state = "main"
target_prof = None
MENU_MAIN = ["สลับโปรไฟล์", "เพิ่มโปรไฟล์ใหม่", "ลบโปรไฟล์", "กลับ"]
MENU_CONFIRM = ["ยกเลิก", "ยืนยัน"]


def reset():
    global state, target_prof
    state = "main"
    target_prof = None


def run(selected_item, context):
    global state, target_prof
    overlay = context["overlay"]

    # 🚨 1. โหลดข้อมูลและเช็คความสมบูรณ์ของโครงสร้าง
    try:
        full_data = load_mapping()
        if not full_data or not isinstance(full_data, dict):
            full_data = {"active_profile": "default", "profiles": {"default": {}}}

        if "profiles" not in full_data:
            full_data["profiles"] = {"default": {}}

        if "active_profile" not in full_data:
            full_data["active_profile"] = "default"

    except Exception as e:
        print(f"❌ [Profile] Load Error: {e}")
        return None

    all_profiles = list(full_data["profiles"].keys())
    active_prof = full_data.get("active_profile", "default")

    # --- Logic ---
    if state == "main":
        if selected_item == "กลับ":
            return "SWITCH:main"

        elif selected_item == "สลับโปรไฟล์":
            state = "select_switch"
            overlay.menu_items = all_profiles + ["กลับ"]
            overlay.center_msg = f"ขณะนี้ใช้: {active_prof}"
            return "UPDATE_UI"

        elif selected_item == "เพิ่มโปรไฟล์ใหม่":
            # สร้างชื่อที่ไม่ซ้ำ
            new_name = f"profile_{len(all_profiles)}"
            while new_name in full_data["profiles"]:
                new_name += "_new"

            # ก๊อปปี้จากตัวปัจจุบันมาเป็นต้นแบบ
            template = full_data["profiles"].get(active_prof, {}).copy()
            full_data["profiles"][new_name] = template

            save_mapping(full_data)
            overlay.center_msg = f"สร้าง {new_name} แล้ว"
            # รีโหลดเมนูเพื่อให้เห็นโปรไฟล์ใหม่
            return "UPDATE_UI"

        elif selected_item == "ลบโปรไฟล์":
            state = "select_delete"
            overlay.menu_items = [p for p in all_profiles if p != "default"] + ["กลับ"]
            return "UPDATE_UI"

    elif state == "select_switch":
        if selected_item == "กลับ":
            state = "main"
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"

        if selected_item in all_profiles:
            full_data["active_profile"] = selected_item
            save_mapping(full_data)
            overlay.center_msg = f"สลับไป {selected_item} แล้ว"
            return "SAVE_MAPPING"  # ✨ บอก Engine ให้รีโหลด

    elif state == "select_delete":
        if selected_item == "กลับ":
            state = "main"
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"

        if selected_item in all_profiles:
            target_prof = selected_item
            state = "confirm_delete"
            overlay.menu_items = MENU_CONFIRM
            overlay.center_msg = f"ยืนยันลบ {target_prof}?"
            return "UPDATE_UI"

    elif state == "confirm_delete":
        if selected_item == "ยืนยัน" and target_prof:
            if target_prof in full_data["profiles"]:
                del full_data["profiles"][target_prof]
                if full_data["active_profile"] == target_prof:
                    full_data["active_profile"] = "default"
                save_mapping(full_data)
                overlay.center_msg = "ลบเรียบร้อย"
            reset()
            overlay.menu_items = MENU_MAIN
            return "SAVE_MAPPING"
        else:
            reset()
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"

    return None
