import importlib
import json
import os
import sys
import time
from pathlib import Path

import pygame

from virtual_input import VirtualInput


# --- ระบบ Portable ---
def get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


PROJECT_ROOT = get_base_path()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from config import setup
except ImportError:
    sys.path.insert(0, str(Path(PROJECT_ROOT)))
    from config import setup


class JoyConEngine:
    """หัวใจหลักของระบบ JoyConMe - รองรับ Dynamic Priority & Cross-Platform & Portable"""

    DEFAULT_TICK_RATE = 60

    def __init__(self):
        self.CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
        self.ACTIONS_DIR = os.path.join(PROJECT_ROOT, "actions")

        self._config_path = os.path.join(self.CONFIG_DIR, "config.json")
        self._mapping_path = os.path.join(self.CONFIG_DIR, "mapping.json")

        self._app_config = {}
        self._mod_mapping = {}

        # เปลี่ยนเป็น List เพื่อให้จัดเรียงลำดับ (Sort) ตาม Priority ได้
        self._actions_list = []

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
        except Exception as e:
            print(f"⚠️ โหลด config.json ไม่สำเร็จ: {e}")
            self._app_config = {}

        try:
            with open(self._mapping_path, "r", encoding="utf-8") as f:
                self._mod_mapping = json.load(f)
        except Exception as e:
            print(f"⚠️ โหลด mapping.json ไม่สำเร็จ: {e}")
            self._mod_mapping = {}

    def _load_actions(self):
        if not os.path.exists(self.ACTIONS_DIR):
            return

        self._actions_list = []
        for filename in os.listdir(self.ACTIONS_DIR):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue

            mod_name = filename[:-3]
            try:
                module = importlib.import_module(f"actions.{mod_name}")
                importlib.reload(module)

                if hasattr(module, "ACTION_INFO") and hasattr(module, "run"):
                    info = module.ACTION_INFO
                    action_id = info.get("id")

                    if action_id:
                        # อ่านค่า Priority และ Blocking (ถ้าไม่มีให้ใช้ค่าเริ่มต้นคือ 0 และ False)
                        priority = info.get("priority", 0)
                        is_blocking = info.get("is_blocking", False)

                        self._actions_list.append(
                            {
                                "id": action_id,
                                "module": module,
                                "priority": priority,
                                "is_blocking": is_blocking,
                            }
                        )
                        print(
                            f"✅ Loaded: {action_id} [Priority: {priority} | Blocking: {is_blocking}]"
                        )
            except Exception as ex:
                print(f"❌ Error loading {mod_name}: {ex}")

        # 🌟 จัดเรียง Action ตาม Priority จากมากไปน้อย
        self._actions_list.sort(key=lambda x: x["priority"], reverse=True)

    def reload_actions(self):
        self._load_actions()
        print("🔄 Actions Reloaded (Dynamic Priority)!")

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
                self._joystick = None
        except Exception:
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
        name = self._app_config.get("system", {}).get("device_name", "JoyConMe")
        try:
            self._ui_virtual = VirtualInput(device_name=name)
        except Exception as ex:
            print(f"❌ สร้าง Virtual Device ไม่สำเร็จ: {ex}")
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
        """รัน 1 Tick ของ Engine แบบ Dynamic Priority"""
        if self._joystick is None:
            self._check_joystick_reconnect()
            return

        pygame.event.get()
        pygame.event.pump()

        # วนลูปทำงานตามลำดับ Priority ที่จัดไว้แล้ว
        for action in self._actions_list:
            result = self._run_action(action["id"], action["module"])

            # ตรวจจับคำสั่งพิเศษ (เช่น เมนูเซ็ตติ้งส่งคำสั่งให้อัปเดตไฟล์)
            if result == "RELOAD":
                self.refresh_config()
                return

            # 🌟 หาก Action นี้ทำงานสำเร็จ (True) และถูกตั้งค่าให้เป็นตัวบล็อก
            if result is True and action["is_blocking"]:
                break  # หยุดการทำงานของ Action ลำดับถัดไปใน Tick นี้ทันที

    def _run_action(self, action_id, module):
        mapping = self._mod_mapping.get(action_id, {})
        try:
            return module.run(
                self._ui_virtual, self._joystick, self._app_config, mapping
            )
        except Exception as e:
            print(f"❌ Error in {action_id}: {e}")
            return None

    def cleanup(self):
        if self._ui_virtual:
            try:
                self._ui_virtual.close()
            except:
                pass
        pygame.quit()
