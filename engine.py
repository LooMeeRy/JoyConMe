import importlib
import json
import os
import time

import pygame
from evdev import UInput
from evdev import ecodes as e


class JoyConEngine:
    def __init__(self):
        # 1. กำหนดเส้นทางและชื่อไฟล์
        self.config_dir = "config"
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.mapping_path = os.path.join(self.config_dir, "mapping.json")
        self.actions_dir = "actions"

        # 2. ตรวจสอบโฟลเดอร์พื้นฐานว่ามีครบไหม
        for folder in [self.config_dir, self.actions_dir]:
            if not os.path.exists(folder):
                os.makedirs(folder)

        # 3. โหลดการตั้งค่า (Config) และการจับคู่ปุ่ม (Mapping)
        self.load_all_configs()

        # 4. เตรียมที่เก็บ Action และเริ่มสแกนโหลดโมดูลจากโฟลเดอร์ actions/
        self.actions = {}
        self.load_actions()

        # 5. เตรียมฮาร์ดแวร์จอยสติ๊กและอุปกรณ์จำลอง (Virtual Mouse)
        self.init_hardware()
        self.init_virtual_device()

    def load_all_configs(self):
        """โหลดไฟล์ตั้งค่า JSON เข้ามาในหน่วยความจำ (RAM)"""
        # โหลดค่าความเร็วและระบบ (app_config)
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.app_config = json.load(f)
            except Exception as ex:
                print(f"⚠️ ไม่สามารถอ่าน config.json ได้: {ex}")
                self.app_config = self._get_default_config()
        else:
            self.app_config = self._get_default_config()
            self.save_app_config()

        # โหลดค่าการตั้งค่าปุ่ม (mod_mapping)
        if os.path.exists(self.mapping_path):
            try:
                with open(self.mapping_path, "r", encoding="utf-8") as f:
                    self.mod_mapping = json.load(f)
            except:
                self.mod_mapping = {}
        else:
            self.mod_mapping = {}

    def _get_default_config(self):
        """ค่าเริ่มต้นกรณีไม่มีไฟล์ตั้งค่า"""
        return {
            "mouse": {
                "speed_x": 15,
                "speed_y": 15,
                "deadzone": 0.15,
                "scroll_delay": 0.08,
            },
            "ui": {"items_per_page": 6, "wait_time_ms": 300},
            "system": {"tick_rate": 60, "device_name": "JoyConMe-Virtual-Mouse"},
        }

    def save_app_config(self):
        """บันทึกการตั้งค่าปัจจุบันลงไฟล์ถาวร"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.app_config, f, indent=4, ensure_ascii=False)

    def load_actions(self):
        """สแกนหาไฟล์ .py ในโฟลเดอร์ actions และดึงความสามารถมาใช้"""
        if not os.path.exists(self.actions_dir):
            return

        for filename in os.listdir(self.actions_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                mod_name = filename[:-3]
                try:
                    # โหลดโมดูลแบบ dynamic
                    module = importlib.import_module(f"actions.{mod_name}")
                    importlib.reload(module)

                    # ตรวจสอบว่าโมดูลมีโครงสร้างตามที่เราต้องการไหม
                    if hasattr(module, "run") and hasattr(module, "ACTION_INFO"):
                        action_id = module.ACTION_INFO["id"]
                        self.actions[action_id] = module
                        print(f"✅ โหลด Action: {action_id} สำเร็จ")
                except Exception as ex:
                    print(f"❌ โหลดไฟล์ '{mod_name}' ไม่สำเร็จ: {ex}")

    def refresh_config(self):
        """สั่งโหลดไฟล์ตั้งค่าใหม่โดยไม่ต้องเปิด-ปิดโปรแกรมใหม่"""
        self.load_all_configs()
        print("🔄 รีโหลดการตั้งค่าเรียบร้อย!")

    def init_hardware(self):
        """ตั้งค่าการรับสัญญาณจากจอยสติ๊ก"""
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"🎮 เชื่อมต่อจอย: {self.joystick.get_name()}")
        else:
            print("❌ ไม่พบจอยสติ๊ก")
            self.joystick = None

    def init_virtual_device(self):
        """สร้างเมาส์จำลองขึ้นมาในระบบ Linux"""
        capabilities = {
            e.EV_REL: (e.REL_X, e.REL_Y, e.REL_WHEEL),
            e.EV_KEY: (e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE),
        }
        name = self.app_config.get("system", {}).get(
            "device_name", "JoyConMe-Virtual-Mouse"
        )
        self.ui_virtual = UInput(capabilities, name=name)

    def get_sleep_time(self):
        """คำนวณเวลาที่ต้องหยุดพักต่อรอบตามค่า Tick Rate"""
        tick_rate = self.app_config.get("system", {}).get("tick_rate", 60)
        return 1.0 / tick_rate

    def run_tick(self):
        """ลูปหลักที่คอยตรวจเช็คการกดปุ่มจอยในทุกๆ เฟรม"""
        if self.joystick is None:
            return

        pygame.event.pump()

        # 1. เช็คเมนูวงกลมก่อน (ถ้าเปิดอยู่จะหยุดการทำงานอื่น)
        if "radial_setup" in self.actions:
            mod = self.actions["radial_setup"]
            mapping = self.mod_mapping.get("radial_setup", {})
            result = mod.run(self.ui_virtual, self.joystick, self.app_config, mapping)

            if result == "RELOAD":
                self.refresh_config()
                return
            elif result is True:
                return

        # 2. รัน Action อื่นๆ (เมาส์, ลูกกลิ้ง ฯลฯ)
        for mod_id, mod in self.actions.items():
            if mod_id == "radial_setup":
                continue
            mapping = self.mod_mapping.get(mod_id, {})
            mod.run(self.ui_virtual, self.joystick, self.app_config, mapping)
