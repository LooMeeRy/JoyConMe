# menus/action_menu.py
import importlib
from menus.utils import get_all_available_actions

MENU_NAME = "ใช้งานแอคชั่น"
MENU_TARGET = "action_main"

state = "main"
all_actions = []
temp_actions = []
MENU_MAIN = ["ใช้งานแอคชั่น", "เพิ่ม/แก้ไขแอคชั่น", "กลับ"]

def reset():
    global state, all_actions, temp_actions
    state = "main"
    all_actions = []
    temp_actions = []

def get_pinned_actions(app_config):
    system = app_config.get("system", {})
    return system.get("pinned_actions", [])

def run(selected_item, context):
    global state, all_actions, temp_actions
    overlay = context["overlay"]
    app_config = context["app_config"]
    pinned_actions = get_pinned_actions(app_config)

    if state == "main":
        if selected_item == "กลับ":
            return "SWITCH:main"
        elif selected_item == "ใช้งานแอคชั่น":
            state = "select_run"
            if not pinned_actions:
                overlay.menu_items = ["(ไม่มีแอคชั่น)", "กลับ"]
            else:
                overlay.menu_items = [p["label"] for p in pinned_actions] + ["กลับ"]
            return "UPDATE_UI"
        elif selected_item == "เพิ่ม/แก้ไขแอคชั่น":
            state = "select_cat"
            all_actions = get_all_available_actions()
            overlay.menu_items = sorted(list(set([a["mod_name"] for a in all_actions]))) + ["กลับ"]
            return "UPDATE_UI"

    elif state == "select_run":
        if selected_item == "กลับ":
            state = "main"
            overlay.menu_items = MENU_MAIN
            return "UPDATE_UI"
        elif selected_item != "(ไม่มีแอคชั่น)":
            target = next((p for p in pinned_actions if p["label"] == selected_item), None)
            if target:
                try:
                    module = importlib.import_module(f"actions.{target['mod']}")
                    # รัน Action ทันทีโดยส่ง trigger_key ที่เลือกไป
                    result = module.run(context["ui_virtual"], context["joystick"], context["app_config"], {}, trigger_key=target["key"])
                    
                    # ปิดเมนูเมื่อใช้งานเสร็จ
                    context["controller"].close_menu()
                    
                    if result == "EXIT":
                        return "EXIT"
                        
                    return None
                except Exception as e:
                    print(f"Error running action {selected_item}: {e}")
                    overlay.center_msg = "เกิดข้อผิดพลาด"
            return "UPDATE_UI"

    elif state == "select_cat":
        if selected_item == "กลับ":
            state = "main"
            overlay.menu_items = MENU_MAIN
        else:
            state = "select_action"
            filtered = [a for a in all_actions if a["mod_name"] == selected_item]
            
            # โชว์เครื่องหมายติ๊กถูกสำหรับแอคชั่นที่มีอยู่ใน Pinned แล้ว
            items = []
            for a in filtered:
                is_pinned = any(p["mod"] == a["mod"] and p["key"] == a["key"] for p in pinned_actions)
                prefix = "✅ " if is_pinned else "⬜ "
                items.append(f"{prefix}{a['label']}")
                
            overlay.menu_items = items + ["กลับ"]
            # เก็บ temp_actions ไว้ชั่วคราวเพื่อให้ดึงข้อมูลได้ใน state ถัดไป
            temp_actions = filtered
        return "UPDATE_UI"

    elif state == "select_action":
        if selected_item == "กลับ":
            state = "select_cat"
            overlay.menu_items = sorted(list(set([a["mod_name"] for a in all_actions]))) + ["กลับ"]
        else:
            # ลบ prefix เพื่อดึงชื่อจริง
            actual_label = selected_item.replace("✅ ", "").replace("⬜ ", "")
            
            action_data = next((a for a in temp_actions if a["label"] == actual_label), None)
            
            if action_data:
                # Toggle presence
                exists = any(p["mod"] == action_data["mod"] and p["key"] == action_data["key"] for p in pinned_actions)
                if exists:
                    pinned_actions = [p for p in pinned_actions if not (p["mod"] == action_data["mod"] and p["key"] == action_data["key"])]
                    overlay.center_msg = f"ลบ {actual_label} แล้ว"
                else:
                    pinned_actions.append({"label": action_data["label"], "mod": action_data["mod"], "key": action_data["key"]})
                    overlay.center_msg = f"เพิ่ม {actual_label} แล้ว"

                if "system" not in app_config:
                    app_config["system"] = {}
                app_config["system"]["pinned_actions"] = pinned_actions
                
                # รีเฟรช UI ให้เครื่องหมายเปลี่ยน
                items = []
                for a in temp_actions:
                    is_pinned = any(p["mod"] == a["mod"] and p["key"] == a["key"] for p in pinned_actions)
                    prefix = "✅ " if is_pinned else "⬜ "
                    items.append(f"{prefix}{a['label']}")
                overlay.menu_items = items + ["กลับ"]
                
                return "SAVE_CONFIG"
        return "UPDATE_UI"

    return None
