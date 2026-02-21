import json
import os


# --- ฟังก์ชันโหลดข้อมูล ---
def get_all_available_actions():
    actions = []
    try:
        # หา Path แบบปลอดภัย
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(current_dir)
        actions_dir = os.path.join(base_dir, "actions")

        if not os.path.exists(actions_dir):
            print(f"[Utils] Warning: Actions folder not found at {actions_dir}")
            return []

        for f in os.listdir(actions_dir):
            if f.endswith(".py") and f != "__init__.py":
                mod_name = f[:-3]
                try:
                    # Import แบบ dynamic
                    module = __import__(f"actions.{mod_name}", fromlist=[""])
                    if hasattr(module, "ACTION_INFO"):
                        info = module.ACTION_INFO
                        cat_name = info.get("name", info["id"])
                        for act in info.get("actions", []):
                            cat = (
                                "analogs" if act.get("type") == "analog" else "buttons"
                            )
                            actions.append(
                                {
                                    "label": act["desc"],
                                    "mod": info["id"],
                                    "mod_name": cat_name,
                                    "cat": cat,
                                    "key": act["key"],
                                }
                            )
                except Exception as e:
                    print(f"[Utils] Failed to load {mod_name}: {e}")
                    continue

    except Exception as e:
        print(f"[Utils] General Error: {e}")

    return actions


def load_recipes():
    path = os.path.join("config", "recipes.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_recipes(data):
    path = os.path.join("config", "recipes.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_mapping():
    path = os.path.join("config", "mapping.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_mapping(data):
    path = os.path.join("config", "mapping.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ✨ เพิ่มฟังก์ชันนี้เข้ามาครับ (ที่ขาดไป)
def load_config():
    path = os.path.join("config", "config.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


# ✨ เพิ่มฟังก์ชันนี้ด้วย
def save_config(data):
    path = os.path.join("config", "config.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# --- Formatting ---
def get_emoji(val):
    if isinstance(val, dict) and "hat" in val:
        d = val["dir"]
        if d[1] == 1:
            return "⬆️"
        if d[1] == -1:
            return "⬇️"
        if d[0] == -1:
            return "⬅️"
        if d[0] == 1:
            return "➡️"
    if isinstance(val, int):
        if val == 0:
            return "🅰️"
        if val == 1:
            return "🅱️"
        if val == 2:
            return "❎"
        if val == 3:
            return "🆈"
        return f"{val}️⃣"
    if isinstance(val, list):
        return "".join([get_emoji(v) for v in val])
    return "❓"


def format_button_name(v):
    if v is None:
        return "(ไม่ได้ตั้งค่า)"
    if isinstance(v, int):
        return f"ปุ่ม {v}"
    if isinstance(v, list):
        return " + ".join([f"ปุ่ม {x}" for x in v])
    if isinstance(v, dict):
        if "hat" in v:
            d = v["dir"]
            dirs = []
            if d[1] == 1:
                dirs.append("ขึ้น")
            if d[1] == -1:
                dirs.append("ลง")
            if d[0] == -1:
                dirs.append("ซ้าย")
            if d[0] == 1:
                dirs.append("ขวา")
            return f"Hat ({' '.join(dirs)})"
    return str(v)
