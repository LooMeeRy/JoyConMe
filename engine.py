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
    sys.path.insert(0, str(Path(__file__).parent))
    from config import setup


class JoyConEngine:
    """หัวใจหลักของระบบ JoyConMe - จัดการ Hardware และ Action Loop"""

    DEFAULT_TICK_RATE = 60
    CONFIG_DIR = "config"
    ACTIONS_DIR = "actions"

    def __init__(self):
        self._config_path = os.path.join(self.CONFIG_DIR, "config.json")
        self._mapping_path = os.path.join(self.CONFIG_DIR, "mapping.json")

        self._app_config = {}
        self._mod_mapping = {}
        self._actions = {}
        self._joystick = None
        self._ui_virtual = None
        self._running = False

        self._init_configs()
        self._init_hardware()
        self._init_virtual_device()
        self._load_actions()

    def _init_configs(self):
        setup.initialize_configs()
        for folder in [self.CONFIG_DIR, self.ACTIONS_DIR]:
            os.makedirs(folder, exist_ok=True)
        self._load_all_configs()

    def _load_all_configs(self):
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._app_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️ โหลด config.json ไม่สำเร็จ: {e}")
            self._app_config = {}

        try:
            with open(self._mapping_path, "r", encoding="utf-8") as f:
                self._mod_mapping = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️ โหลด mapping.json ไม่สำเร็จ: {e}")
            self._mod_mapping = {}

    def save_app_config(self):
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._app_config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ บันทึก config ไม่สำเร็จ: {e}")
            return False

    def _load_actions(self):
        if not os.path.exists(self.ACTIONS_DIR):
            print(f"⚠️ ไม่พบโฟลเดอร์ {self.ACTIONS_DIR}")
            return

        for filename in os.listdir(self.ACTIONS_DIR):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue

            mod_name = filename[:-3]
            try:
                module = importlib.import_module(f"{self.ACTIONS_DIR}.{mod_name}")
                importlib.reload(module)

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
        self._actions.clear()
        self._load_actions()
        print("🔄 Actions Reloaded!")

    def refresh_config(self):
        self._load_all_configs()
        print("🔄 Config Reloaded!")

    def _init_hardware(self):
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
        if self._joystick is None:
            pygame.joystick.quit()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self._init_hardware()
                return True
        return False

    def _init_virtual_device(self):
        """สร้าง Virtual Input Device — รองรับทั้งเมาส์และคีย์บอร์ด"""

        # รวม keyboard keys ทั้งหมดที่ต้องใช้
        keyboard_keys = [
            # a-z
            e.KEY_A,
            e.KEY_B,
            e.KEY_C,
            e.KEY_D,
            e.KEY_E,
            e.KEY_F,
            e.KEY_G,
            e.KEY_H,
            e.KEY_I,
            e.KEY_J,
            e.KEY_K,
            e.KEY_L,
            e.KEY_M,
            e.KEY_N,
            e.KEY_O,
            e.KEY_P,
            e.KEY_Q,
            e.KEY_R,
            e.KEY_S,
            e.KEY_T,
            e.KEY_U,
            e.KEY_V,
            e.KEY_W,
            e.KEY_X,
            e.KEY_Y,
            e.KEY_Z,
            # special keys
            e.KEY_SPACE,
            e.KEY_ENTER,
            e.KEY_BACKSPACE,
            e.KEY_LEFTSHIFT,
            e.KEY_CAPSLOCK,
            # ปุ่มเมาส์
            e.BTN_LEFT,
            e.BTN_RIGHT,
            e.BTN_MIDDLE,
        ]

        capabilities = {
            e.EV_REL: (e.REL_X, e.REL_Y, e.REL_WHEEL),
            e.EV_KEY: keyboard_keys,
        }

        name = self._app_config.get("system", {}).get("device_name", "JoyConMe")

        try:
            self._ui_virtual = UInput(capabilities, name=name)
            print(f"🖱️⌨️ Virtual Device: {name}")
        except Exception as ex:
            print(f"❌ สร้าง Virtual Device ไม่สำเร็จ: {ex}")
            print("💡 ตรวจสอบว่ารันด้วย sudo หรือมีสิทธิ์ /dev/uinput")
            raise

    @property
    def joystick(self):
        return self._joystick

    @property
    def ui_virtual(self):
        return self._ui_virtual

    def get_sleep_time(self):
        tick_rate = self._app_config.get("system", {}).get(
            "tick_rate", self.DEFAULT_TICK_RATE
        )
        return 1.0 / max(1, tick_rate)

    def run_tick(self):
        """รัน 1 Tick ของ Engine"""
        if self._joystick is None:
            self._check_joystick_reconnect()
            return

        pygame.event.get()
        pygame.event.pump()

        # Priority 1: Radial Menu
        if "radial_setup" in self._actions:
            result = self._run_action("radial_setup")
            if result == "RELOAD":
                self.refresh_config()
                return
            if result is True:
                return

        # Priority 2: Keyboard (กิน input ทั้งหมดถ้า active)
        if "keyboard" in self._actions:
            result = self._run_action("keyboard")
            if result is True:
                return

        # Priority 3: Sequence Engine
        if "sequence_engine" in self._actions:
            result = self._run_action("sequence_engine")
            if result is True:
                return

        # Priority 4: Other Actions (mouse, exit, etc.)
        for action_id, module in self._actions.items():
            if action_id in ["radial_setup", "keyboard", "sequence_engine"]:
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
        print("\n🧹 Cleaning up...")
        if self._ui_virtual:
            try:
                self._ui_virtual.close()
            except:
                pass
        pygame.quit()
        print("👋 Goodbye!")
