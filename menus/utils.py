import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_project_root() -> Path:
    """หา Root ของโปรเจค"""
    # เริ่มจากไฟล์นี้
    current = Path(__file__).resolve().parent
    # ขึ้นไป 1 ระดับ (จาก menus/ ไป root)
    return current.parent


def get_config_path(filename: str) -> Path:
    """หา path ของไฟล์ config"""
    return get_project_root() / "config" / filename


def load_json_safe(filepath: Path, default: Any = None) -> Any:
    """โหลด JSON อย่างปลอดภัย"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ โหลด {filepath} ไม่สำเร็จ: {e}")
        return default if default is not None else {}


def save_json_safe(filepath: Path, data: Any) -> bool:
    """บันทึก JSON อย่างปลอดภัย"""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ บันทึก {filepath} ไม่สำเร็จ: {e}")
        return False


# --- Config Functions ---
def load_config() -> Dict:
    return load_json_safe(get_config_path("config.json"), {})


def save_config(data: Dict) -> bool:
    return save_json_safe(get_config_path("config.json"), data)


def load_mapping() -> Dict:
    return load_json_safe(get_config_path("mapping.json"), {})


def save_mapping(data: Dict) -> bool:
    return save_json_safe(get_config_path("mapping.json"), data)


def load_recipes() -> List[Dict]:
    return load_json_safe(get_config_path("recipes.json"), [])


def save_recipes(data: List[Dict]) -> bool:
    return save_json_safe(get_config_path("recipes.json"), data)


# --- Action Scanner ---
def get_all_available_actions() -> List[Dict]:
    """สแกน Action Modules ทั้งหมด"""
    actions = []
    actions_dir = get_project_root() / "actions"

    if not actions_dir.exists():
        print(f"⚠️ ไม่พบโฟลเดอร์ actions")
        return actions

    for f in actions_dir.glob("*.py"):
        if f.name.startswith("_"):
            continue

        mod_name = f.stem
        try:
            # ใช้ importlib.util แทน __import__ เพื่อความปลอดภัย
            import importlib.util

            spec = importlib.util.spec_from_file_location(f"actions.{mod_name}", f)
            if not spec or not spec.loader:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "ACTION_INFO"):
                info = module.ACTION_INFO
                cat_name = info.get("name", info.get("id", "Unknown"))

                for act in info.get("actions", []):
                    cat = "analogs" if act.get("type") == "analog" else "buttons"
                    actions.append(
                        {
                            "label": act.get("desc", act.get("key", "Unknown")),
                            "mod": info.get("id", mod_name),
                            "mod_name": cat_name,
                            "cat": cat,
                            "key": act.get("key", ""),
                        }
                    )
        except Exception as e:
            print(f"⚠️ โหลด {mod_name} ไม่สำเร็จ: {e}")
            continue

    return actions


# --- Formatting ---
def get_emoji(val: Any) -> str:
    """แปลง input เป็น emoji"""
    if isinstance(val, dict) and "hat" in val:
        d = val.get("dir", [0, 0])
        if d[1] == 1:
            return "⬆️"
        if d[1] == -1:
            return "⬇️"
        if d[0] == -1:
            return "⬅️"
        if d[0] == 1:
            return "➡️"

    if isinstance(val, int):
        emoji_map = {0: "🅰️", 1: "🅱️", 2: "🆈", 3: "❎"}
        return emoji_map.get(val, f"{val}️⃣")

    if isinstance(val, list):
        return "".join([get_emoji(v) for v in val])

    return "❓"


def format_button_name(v: Any) -> str:
    """แปลงค่า input เป็นข้อความอ่านง่าย"""
    if v is None:
        return "(ไม่ได้ตั้งค่า)"

    if isinstance(v, int):
        return f"ปุ่ม {v}"

    if isinstance(v, list):
        return " + ".join([f"ปุ่ม {x}" for x in v])

    if isinstance(v, dict) and "hat" in v:
        d = v.get("dir", [0, 0])
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


def normalize_input(val: Any) -> Any:
    """Normalize input value สำหรับเปรียบเทียบ"""
    if isinstance(val, dict) and "hat" in val:
        d = val.get("dir")
        if isinstance(d, tuple):
            return {"hat": val["hat"], "dir": list(d)}
        return val
    return val
