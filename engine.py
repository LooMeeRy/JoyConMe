import importlib
import os

import pygame
from evdev import UInput
from evdev import ecodes as e

from config.loader import load_json
from config.setup import initialize_configs


class InputEngine:
    def __init__(self):
        # 1. เตรียมไฟล์ Config และ Mapping
        initialize_configs()
        self.app_config = load_json("config.json")
        self.app_mapping = load_json("mapping.json")

        # 2. เตรียม Virtual Input
        capabilities = {
            e.EV_REL: (e.REL_X, e.REL_Y),
            e.EV_KEY: (e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE),
        }
        self.ui = UInput(events=capabilities, name="JoyConMe-Virtual-Mouse")

        # 3. เตรียมจอยสติ๊ก
        pygame.init()
        pygame.joystick.init()
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"🎮 พร้อมใช้งานจอย: {self.joystick.get_name()}")
        else:
            print("❌ ไม่พบจอยสติ๊ก")

        # 4. โหลด Actions ทั้งหมด
        self.actions = {}
        self.load_actions()

    def load_actions(self):
        actions_dir = os.path.join(os.path.dirname(__file__), "actions")
        if not os.path.exists(actions_dir):
            return
        for f in os.listdir(actions_dir):
            if f.endswith(".py") and f != "__init__.py":
                mod_name = f[:-3]
                try:
                    module = importlib.import_module(f"actions.{mod_name}")
                    if hasattr(module, "ACTION_INFO"):
                        self.actions[module.ACTION_INFO["id"]] = module
                        print(f"📦 Loaded: {module.ACTION_INFO['name']}")
                except Exception as ex:
                    print(f"⚠️ Load Error {f}: {ex}")

    def run_tick(self):
        """ทำงาน 1 รอบลูป"""
        if not self.joystick:
            return

        pygame.event.pump()

        # ดึง Mapping ล่าสุดมาใช้ (เผื่อมีการอัปเดตไฟล์)
        self.app_mapping = load_json("mapping.json")

        for mod_id, module in self.actions.items():
            # ดึง Mapping เฉพาะของโมดูลนี้
            mod_mapping = self.app_mapping.get(mod_id, {})
            analogs = mod_mapping.get("analogs", {})
            buttons = mod_mapping.get("buttons", {})

            # เรียกฟังก์ชันในไฟล์ Action
            if mod_id == "mouse_control":
                # ส่งข้อมูลความเร็วจาก Config และข้อมูลแกนจาก Mapping
                module.process_mouse_movement(
                    self.ui,
                    self.joystick,
                    self.app_config.get("mouse", {}),
                    analogs,
                    buttons,
                )

    def get_sleep_time(self):
        return self.app_config.get("system", {}).get("sleep_time", 0.01)
