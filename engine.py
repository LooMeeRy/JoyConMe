import importlib
import os
import time

import pygame
from evdev import UInput
from evdev import ecodes as e
from PySide6.QtWidgets import QApplication

from config.loader import load_json
from config.setup import initialize_configs


class InputEngine:
    def __init__(self):
        # 1. จัดการระบบ UI (PySide6)
        # สร้าง QApplication instance ทิ้งไว้เพื่อให้ Action ต่างๆ เรียกใช้ UI ได้
        self.qt_app = QApplication.instance() or QApplication([])

        # 2. เตรียมไฟล์ Config และ Mapping
        initialize_configs()
        self.refresh_config()

        # 3. เตรียม Virtual Input (เมาส์และปุ่มพื้นฐาน)
        capabilities = {
            e.EV_REL: (e.REL_X, e.REL_Y),
            e.EV_KEY: (e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE, e.KEY_ENTER, e.KEY_ESC),
        }
        self.ui_virtual = UInput(events=capabilities, name="JoyConMe-Engine-Input")

        # 4. เตรียมจอยสติ๊ก
        pygame.init()
        pygame.joystick.init()
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"🎮 Connected: {self.joystick.get_name()}")
        else:
            print("❌ No Joystick Found")

        # 5. โหลด Actions ทั้งหมดจากโฟลเดอร์ actions/
        self.actions = {}
        self.load_actions()

    def refresh_config(self):
        """โหลดค่าจากไฟล์ JSON ใหม่"""
        self.app_config = load_json("config.json")
        self.app_mapping = load_json("mapping.json")

    def load_actions(self):
        """สแกนโฟลเดอร์ actions/ เพื่อโหลดโมดูลแบบ Dynamic"""
        actions_dir = os.path.join(os.path.dirname(__file__), "actions")
        if not os.path.exists(actions_dir):
            return

        for f in os.listdir(actions_dir):
            if f.endswith(".py") and f != "__init__.py":
                mod_name = f[:-3]
                try:
                    # นำเข้าโมดูล (Import)
                    module = importlib.import_module(f"actions.{mod_name}")
                    if hasattr(module, "ACTION_INFO"):
                        self.actions[module.ACTION_INFO["id"]] = module
                        print(f"📦 Loaded Action: {module.ACTION_INFO['name']}")
                except Exception as ex:
                    print(f"⚠️ Error loading {f}: {ex}")

    def run_tick(self):
        """ทำงาน 1 รอบลูป (เรียกใช้จาก main.py)"""
        if not self.joystick:
            return

        # อัปเดตเหตุการณ์ของ UI (ทำให้หน้าต่าง Overlay ไม่ค้าง)
        self.qt_app.processEvents()

        # อัปเดตเหตุการณ์ของจอยสติ๊ก
        pygame.event.pump()

        # ตัวแปรสำหรับเช็คว่ามี Action ไหนขอ 'ล็อค' การควบคุมไว้หรือไม่
        exclusive_mode = False

        # --- ลำดับการรัน 1: รัน Action พิเศษ (เช่น Radial Menu Setup) ---
        # เราให้ระบบ Setup มีสิทธิ์ทำงานก่อนเพื่อดูว่าจะเปิดเมนูไหม
        if "radial_setup" in self.actions:
            mod = self.actions["radial_setup"]
            mapping = self.app_mapping.get("radial_setup", {})
            result = mod.run(self.ui_virtual, self.joystick, self.app_config, mapping)

            # ✨ เช็คสัญญาณขอรีโหลดไฟล์ JSON
            if result == "RELOAD":
                print("🔄 ตรวจพบการเปลี่ยนแปลง! กำลังโหลด mapping.json ใหม่...")
                self.refresh_config()  # โหลดไฟล์ใหม่ทันที!
                exclusive_mode = False
            else:
                exclusive_mode = result

        # --- ลำดับการรัน 2: รัน Action ทั่วไป (เช่น ขยับเมาส์) ---
        # ถ้าไม่มีการเปิดเมนูวงกลมอยู่ (Not Exclusive) ให้รัน Action อื่นๆ ตามปกติ
        if not exclusive_mode:
            for mod_id, module in self.actions.items():
                if mod_id == "radial_setup":
                    continue  # ข้ามตัวที่รันไปแล้ว

                mod_mapping = self.app_mapping.get(mod_id, {})

                # ตรวจสอบฟังก์ชันการรัน (รองรับทั้งแบบ .run() และ .process_mouse_movement())
                if hasattr(module, "run"):
                    module.run(
                        self.ui_virtual, self.joystick, self.app_config, mod_mapping
                    )
                elif mod_id == "mouse_control" and hasattr(
                    module, "process_mouse_movement"
                ):
                    module.process_mouse_movement(
                        self.ui_virtual,
                        self.joystick,
                        self.app_config.get("mouse", {}),
                        mod_mapping.get("analogs", {}),
                        mod_mapping.get("buttons", {}),
                    )

    def get_sleep_time(self):
        return self.app_config.get("system", {}).get("sleep_time", 0.01)
