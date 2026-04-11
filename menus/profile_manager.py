# menus/profile_manager.py
import time

from menus.utils import load_mapping, save_mapping

# ✨ ระบบ Plug & Play
MENU_NAME = "จัดการโปรไฟล์"
MENU_TARGET = "profile_manager"

# --- State ---
state = "main"
target_prof = None

MENU_MAIN = ["สลับโปรไฟล์", "เพิ่มโปรไฟล์ใหม่", "จัดการโปรไฟล์", "กลับ"]
# ลบเมนูเปลี่ยนชื่อออกแล้ว เหลือแค่ ใช้งาน กับ ลบ
MENU_MANAGE = ["✅ ใช้งาน", "❌ ลบโปรไฟล์", "กลับ"]
MENU_CONFIRM = ["ยกเลิก", "ยืนยัน"]


def reset():
    global state, target_prof
    state = "main"
    target_prof = None


def run(selected_item, context):
    global state, target_prof
    overlay = context["overlay"]

    # 🚨 โหลดข้อมูลและเช็คความสมบูรณ์ของโครงสร้าง
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

    # --- 1. หน้าหลัก ---
    if state == "main":
        if selected_item == "กลับ":
            return "SWITCH:main"

        elif selected_item == "สลับโปรไฟล์":
            state = "select_switch"
            overlay.menu_items = all_profiles + ["กลับ"]
            overlay.center_msg = f"ขณะนี้ใช้: {active_prof}"
            return "UPDATE_UI"

        elif selected_item == "เพิ่มโปรไฟล์ใหม่":
            # กลับมาใช้ระบบสุ่มชื่ออัตโนมัติ (ชัวร์ 100%)
            new_name = f"profile_{len(all_profiles)}"
            while new_name in full_data["profiles"]:
                new_name += "_new"

            template = full_data["profiles"].get(active_prof, {}).copy()
            full_data["profiles"][new_name] = template

            save_mapping(full_data)
            overlay.center_msg = f"สร้าง {new_name} แล้ว"
            return "UPDATE_UI"

        elif selected_item == "จัดการโปรไฟล์":
            state = "select_manage"
            overlay.menu_items = all_profiles + ["กลับ"]
            return "UPDATE_UI"

    # --- 2. หน้าสลับโปรไฟล์ ---
    elif state == "select_switch":
        if selected_item == "กลับ":
            reset()
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"

        if selected_item in all_profiles:
            full_data["active_profile"] = selected_item
            save_mapping(full_data)
            overlay.center_msg = f"สลับไป {selected_item} แล้ว"
            reset()
            overlay.menu_items = MENU_MAIN
            return "SAVE_MAPPING"

    # --- 3. เลือกโปรไฟล์ที่จะจัดการ ---
    elif state == "select_manage":
        if selected_item == "กลับ":
            reset()
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"

        if selected_item in all_profiles:
            target_prof = selected_item
            state = "manage_opts"
            overlay.menu_items = MENU_MANAGE
            overlay.center_msg = f"โปรไฟล์:\n{target_prof}"
            return "UPDATE_UI"

    # --- 4. จัดการโปรไฟล์ (สลับ/ลบ) ---
    elif state == "manage_opts":
        if selected_item == "กลับ":
            state = "select_manage"
            overlay.menu_items = all_profiles + ["กลับ"]
            return "UPDATE_UI"

        elif selected_item == "✅ ใช้งาน":
            full_data["active_profile"] = target_prof
            save_mapping(full_data)
            overlay.center_msg = f"ใช้งาน {target_prof} แล้ว"
            reset()
            overlay.menu_items = MENU_MAIN
            return "SAVE_MAPPING"

        elif selected_item == "❌ ลบโปรไฟล์":
            if target_prof == "default":
                overlay.center_msg = "ลบโปรไฟล์ default ไม่ได้!"
                return "UPDATE_UI"
            state = "confirm_delete"
            overlay.menu_items = MENU_CONFIRM
            overlay.center_msg = f"ยืนยันลบ {target_prof}?"
            return "UPDATE_UI"

    # --- 5. ยืนยันการลบ ---
    elif state == "confirm_delete":
        if selected_item == "ยืนยัน" and target_prof:
            del full_data["profiles"][target_prof]
            if full_data["active_profile"] == target_prof:
                full_data["active_profile"] = "default"
            save_mapping(full_data)
            overlay.center_msg = "ลบเรียบร้อย"
            reset()
            overlay.menu_items = MENU_MAIN
            return "SAVE_MAPPING"
        else:
            state = "manage_opts"
            overlay.menu_items = MENU_MANAGE
            return "UPDATE_UI"

    return None
