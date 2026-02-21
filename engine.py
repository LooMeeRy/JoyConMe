import importlib
import json
import os
import time

import pygame
from evdev import UInput
from evdev import ecodes as e

# Import Setup
from config import setup


class JoyConEngine:
    def __init__(self):
        self.config_dir = "config"
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.mapping_path = os.path.join(self.config_dir, "mapping.json")
        self.actions_dir = "actions"

        # 1. สร้างไฟล์ Config เริ่มต้นจาก setup.py ก่อน
        setup.initialize_configs()

        for folder in [self.config_dir, self.actions_dir]:
            if not os.path.exists(folder):
                os.makedirs(folder)

        # 2. โหลด Config
        self.load_all_configs()
        self.actions = {}
        self.load_actions()
        self.init_hardware()
        self.init_virtual_device()

    def load_all_configs(self):
        # โหลด Config
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.app_config = json.load(f)
            except:
                self.app_config = {}  # Fallback
        else:
            self.app_config = {}

        # โหลด Mapping
        if os.path.exists(self.mapping_path):
            try:
                with open(self.mapping_path, "r", encoding="utf-8") as f:
                    self.mod_mapping = json.load(f)
            except:
                self.mod_mapping = {}
        else:
            self.mod_mapping = {}

    def save_app_config(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.app_config, f, indent=4, ensure_ascii=False)

    def load_actions(self):
        if not os.path.exists(self.actions_dir):
            return
        for filename in os.listdir(self.actions_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                mod_name = filename[:-3]
                try:
                    module = importlib.import_module(f"actions.{mod_name}")
                    importlib.reload(module)
                    if hasattr(module, "run") and hasattr(module, "ACTION_INFO"):
                        action_id = module.ACTION_INFO["id"]
                        self.actions[action_id] = module
                        print(f"✅ Loaded: {action_id}")
                except Exception as ex:
                    print(f"❌ Error loading {mod_name}: {ex}")

    def refresh_config(self):
        self.load_all_configs()
        print("🔄 Config Reloaded!")

    def init_hardware(self):
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"🎮 Joystick: {self.joystick.get_name()}")
        else:
            print("❌ No joystick found")
            self.joystick = None

    def init_virtual_device(self):
        capabilities = {
            e.EV_REL: (e.REL_X, e.REL_Y, e.REL_WHEEL),
            e.EV_KEY: (e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE),
        }
        name = self.app_config.get("system", {}).get("device_name", "JoyConMe")
        self.ui_virtual = UInput(capabilities, name=name)

    def get_sleep_time(self):
        tick_rate = self.app_config.get("system", {}).get("tick_rate", 60)
        return 1.0 / tick_rate

    def run_tick(self):
        if self.joystick is None:
            return
        pygame.event.pump()

        # Priority 1: Radial Menu
        if "radial_setup" in self.actions:
            mod = self.actions["radial_setup"]
            mapping = self.mod_mapping.get("radial_setup", {})
            result = mod.run(self.ui_virtual, self.joystick, self.app_config, mapping)
            if result == "RELOAD":
                self.refresh_config()
                return
            elif result is True:
                return

        # Priority 2: Sequence Engine
        if "sequence_engine" in self.actions:
            mod = self.actions["sequence_engine"]
            mapping = self.mod_mapping.get("sequence_engine", {})
            result = mod.run(self.ui_virtual, self.joystick, self.app_config, mapping)
            if result is True:
                return

        # Priority 3: Others
        for mod_id, mod in self.actions.items():
            if mod_id in ["radial_setup", "sequence_engine"]:
                continue
            mapping = self.mod_mapping.get(mod_id, {})
            mod.run(self.ui_virtual, self.joystick, self.app_config, mapping)
