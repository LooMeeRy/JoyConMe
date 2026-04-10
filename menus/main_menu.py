# menus/main_menu.py
import importlib
import sys
from pathlib import Path

MENU_ITEMS = []
_loaded_menus = {}
_target_menus = {}  # เพิ่ม Registry สำหรับเก็บ target ของแต่ละเมนู


def reload_menus():
    """ฟังก์ชันสำหรับสแกนหาไฟล์เมนูใหม่ๆ แบบอัตโนมัติ (Plug & Play)"""
    global MENU_ITEMS, _loaded_menus, _target_menus
    MENU_ITEMS.clear()
    _loaded_menus.clear()
    _target_menus.clear()

    # ลงทะเบียนตัวเองเป็น target "main" เสมอ
    _target_menus["main"] = sys.modules[__name__]

    # ชี้ไปที่โฟลเดอร์ menus/
    menu_dir = Path(__file__).parent

    # ค้นหาไฟล์ .py ทั้งหมดในโฟลเดอร์
    for file_path in menu_dir.glob("*.py"):
        mod_name = file_path.stem

        # ข้ามไฟล์ระบบและไฟล์ตัวเอง
        if mod_name in ["main_menu", "utils", "__init__"] or mod_name.startswith("_"):
            continue

        try:
            module = importlib.import_module(f"menus.{mod_name}")
            importlib.reload(module)  # บังคับ Reload โค้ดใหม่เสมอเวลาเปิดเมนู

            # นำเข้าชื่อเมนู
            if hasattr(module, "MENU_NAME"):
                _loaded_menus[module.MENU_NAME] = module
                MENU_ITEMS.append(module.MENU_NAME)

            # นำเข้าเป้าหมายของเมนู (เพื่อใช้เวลาสลับหน้า)
            if hasattr(module, "MENU_TARGET"):
                _target_menus[module.MENU_TARGET] = module

        except Exception as e:
            print(f"⚠️ [MainMenu] โหลดไฟล์เมนู {mod_name} ไม่สำเร็จ: {e}")

    # เพิ่มปุ่ม ปิดเมนู ไว้ท้ายสุดเสมอ
    MENU_ITEMS.append("ปิดเมนู")


def get_menu_module(target_id):
    """ส่งคืน Module ของเมนูตาม target ที่ร้องขอ"""
    return _target_menus.get(target_id)


# สแกนเมนูครั้งแรกเมื่อไฟล์ถูกโหลด
reload_menus()


def run(selected_item, context):
    if selected_item == "ปิดเมนู":
        return "CLOSE_MENU"

    # ถ้าผู้ใช้เลือกเมนูที่มีการโหลดไว้แบบอัตโนมัติ
    if selected_item in _loaded_menus:
        module = _loaded_menus[selected_item]

        # กรณีที่ 1: เป็นเมนูที่มีหน้าต่างย่อย (ให้สลับหน้าไป)
        if hasattr(module, "MENU_TARGET"):
            return f"SWITCH:{module.MENU_TARGET}"

        # กรณีที่ 2: เป็นเมนูที่กดแล้วทำงานเลยทันที (เช่น คีย์บอร์ด)
        elif hasattr(module, "run"):
            return module.run(selected_item, context)

    return None
