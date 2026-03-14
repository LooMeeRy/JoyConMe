import importlib
import json
import os
import sys
import time
from pathlib import Path

import pygame
from evdev import UInput
from evdev import ecodes as e

# Import Setup - ใช้ try-except ป้องกัน Import Error
try:
    from config import setup
except ImportError:
    # Fallback ถ้า import ไม่ได้ (รันไฟล์โดยตรง)
    sys.path.insert(0, str(Path(__file__).parent))
    from config import setup


class JoyConEngine:
    """หัวใจหลักของระบบ JoyConMe - จัดการ Hardware และ Action Loop"""

    # Class constants
    DEFAULT_TICK_RATE = 60
    CONFIG_DIR = "config"
    ACTIONS_DIR = "actions"

    def __init__(self):
        self._config_path = os.path.join(self.CONFIG_DIR, "config.json")
        self._mapping_path = os.path.join(self.CONFIG_DIR, "mapping.json")

        # State
        self._app_config = {}
        self._mod_mapping = {}
        self._actions = {}
        self._joystick = None
        self._ui_virtual = None
        self._running = False

        # Initialize
        self._init_configs()
        self._init_hardware()
        self._init_virtual_device()
        self._load_actions()

    def _init_configs(self):
        """โหลดหรือสร้าง config เริ่มต้น"""
        setup.initialize_configs()

        # สร้างโฟลเดอร์ถ้ายังไม่มี
        for folder in [self.CONFIG_DIR, self.ACTIONS_DIR]:
            os.makedirs(folder, exist_ok=True)

        self._load_all_configs()

    def _load_all_configs(self):
        """โหลด config และ mapping จากไฟล์"""
        # Load app config
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._app_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️ โหลด config.json ไม่สำเร็จ: {e}")
            self._app_config = {}

        # Load mapping
        try:
            with open(self._mapping_path, "r", encoding="utf-8") as f:
                self._mod_mapping = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️ โหลด mapping.json ไม่สำเร็จ: {e}")
            self._mod_mapping = {}

    def save_app_config(self):
        """บันทึก config ปัจจุบันลงไฟล์"""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._app_config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ บันทึก config ไม่สำเร็จ: {e}")
            return False

    def _load_actions(self):
        """โหลด Action Modules ทั้งหมดจากโฟลเดอร์ actions/"""
        if not os.path.exists(self.ACTIONS_DIR):
            print(f"⚠️ ไม่พบโฟลเดอร์ {self.ACTIONS_DIR}")
            return

        for filename in os.listdir(self.ACTIONS_DIR):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue

            mod_name = filename[:-3]
            try:
                module = importlib.import_module(f"{self.ACTIONS_DIR}.{mod_name}")
                importlib.reload(module)  # รองรับ Hot-reload

                if hasattr(module, "ACTION_INFO") and hasattr(module, "run"):
                    action_id = module.ACTION_INFO.get("id")
                    if action_id:
                        self._actions[action_id] = module
                        print(f"✅ Loaded: {action_id}")
                else:
                    print(f"⚠️ {mod_name} ไม่มี ACTION_INFO หรือ run()")

            except Exception as ex:
                print(f"❌ Error loading {mod_name}: {ex}")

    def reload_actions(self):
        """โหลด Action ใหม่ (สำหรับ Development)"""
        self._actions.clear()
        self._load_actions()
        print("🔄 Actions Reloaded!")

    def refresh_config(self):
        """โหลด Config ใหม่"""
        self._load_all_configs()
        print("🔄 Config Reloaded!")

    def _init_hardware(self):
        """เริ่มต้น Pygame Joystick"""
        try:
            pygame.init()
            pygame.joystick.init()

            if pygame.joystick.get_count() > 0:
                self._joystick = pygame.joystick.Joystick(0)
                self._joystick.init()
                print(f"🎮 Joystick: {self._joystick.get_name()}")
            else:
                print("⚠️ No joystick found - รอจอยเสียบ...")
                self._joystick = None

        except Exception as e:
            print(f"❌ Pygame Init Error: {e}")
            self._joystick = None

    def _check_joystick_reconnect(self):
        """ตรวจสอบการเชื่อมต่อจอยใหม่"""
        if self._joystick is None:
            pygame.joystick.quit()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self._init_hardware()
                return True
        return False

    def _init_virtual_device(self):
        """สร้าง Virtual Input Device สำหรับควบคุมเมาส์"""
        capabilities = {
            e.EV_REL: (e.REL_X, e.REL_Y, e.REL_WHEEL),
            e.EV_KEY: (e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE),
        }
        name = self._app_config.get("system", {}).get("device_name", "JoyConMe")

        try:
            self._ui_virtual = UInput(capabilities, name=name)
            print(f"🖱️ Virtual Device: {name}")
        except Exception as ex:
            print(f"❌ สร้าง Virtual Device ไม่สำเร็จ: {ex}")
            print("💡 ตรวจสอบว่ารันด้วย sudo หรือมีสิทธิ์ /dev/uinput")
            raise

    @property
    def joystick(self):
        """Getter สำหรับ Joystick"""
        return self._joystick

    @property
    def ui_virtual(self):
        """Getter สำหรับ Virtual Device"""
        return self._ui_virtual

    def get_sleep_time(self):
        """คำนวณเวลาพักตาม tick rate"""
        tick_rate = self._app_config.get("system", {}).get(
            "tick_rate", self.DEFAULT_TICK_RATE
        )
        return 1.0 / max(1, tick_rate)

    def run_tick(self):
        """รัน 1 Tick ของ Engine"""
        # ตรวจสอบจอยใหม่ถ้าหลุด
        if self._joystick is None:
            self._check_joystick_reconnect()
            return

        pygame.event.pump()

        # Priority 1: Radial Menu (กิน input ทั้งหมดถ้า active)
        if "radial_setup" in self._actions:
            result = self._run_action("radial_setup")
            if result == "RELOAD":
                self.refresh_config()
                return
            if result is True:
                return

        # Priority 2: Sequence Engine
        if "sequence_engine" in self._actions:
            result = self._run_action("sequence_engine")
            if result is True:
                return

        # Priority 3: Other Actions
        for action_id, module in self._actions.items():
            if action_id in ["radial_setup", "sequence_engine"]:
                continue
            self._run_action(action_id, module)

    def _run_action(self, action_id, module=None):
        """รัน Action ที่ระบุ พร้อม Error Handling"""
        if module is None:
            module = self._actions.get(action_id)
            if not module:
                return None

        mapping = self._mod_mapping.get(action_id, {})

        try:
            return module.run(
                self._ui_virtual, self._joystick, self._app_config, mapping
            )
        except Exception as e:
            print(f"❌ Error in {action_id}: {e}")
            return None

    def cleanup(self):
        """ปิดทรัพยากรทั้งหมด"""
        print("\n🧹 Cleaning up...")
        if self._ui_virtual:
            try:
                self._ui_virtual.close()
            except:
                pass
        pygame.quit()
        print("👋 Goodbye!")
