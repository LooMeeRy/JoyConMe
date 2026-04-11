import importlib
import json
import os
import sys
import time
from pathlib import Path

# 🔹 ตั้งค่า Environment สำหรับ Linux/CachyOS
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

import pygame
from evdev import UInput
from evdev import ecodes as e

# ✨ Import ฟังก์ชันจัดการ Mapping จาก utils
try:
    from menus.utils import load_mapping
except ImportError:

    def load_mapping():
        path = "config/mapping.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"active_profile": "default", "profiles": {"default": {}}}


try:
    from config import setup
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from config import setup


class JoyConEngine:
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

        self._init_configs()
        self._init_hardware()
        self._init_virtual_device()
        self._load_actions()

    def _init_configs(self):
        setup.initialize_configs()
        if not os.path.exists(self.CONFIG_DIR):
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
        self.reload_mapping_from_disk()
        self._load_app_config()

    def _load_app_config(self):
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._app_config = json.load(f)
            if "system" not in self._app_config:
                self._app_config["system"] = {}
            self._app_config["system"]["action_shield"] = False
        except:
            self._app_config = {"system": {"action_shield": False}}

    def reload_mapping_from_disk(self):
        """✨ โหลด Mapping ใหม่จากไฟล์และ Update แรมทันที"""
        # print("📥 [Engine] Reloading mapping.json from disk...")
        raw = load_mapping()

        if "profiles" not in raw:
            print("🔄 [Engine] Upgrading mapping.json to Profile System...")
            self._mod_mapping = {
                "active_profile": "default",
                "profiles": {"default": raw},
            }
            self.save_mapping()
        else:
            self._mod_mapping = raw

        return self._mod_mapping

    def save_app_config(self):
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._app_config, f, indent=4, ensure_ascii=False)
            return True
        except:
            return False

    def save_mapping(self):
        try:
            with open(self._mapping_path, "w", encoding="utf-8") as f:
                json.dump(self._mod_mapping, f, indent=4, ensure_ascii=False)
            return True
        except:
            return False

    def _load_actions(self):
        if not os.path.exists(self.ACTIONS_DIR):
            return
        print("\n" + "=" * 50)
        print("📦 LOADING ACTIONS & SYSTEM MODULES")
        print("-" * 50)
        loaded_count = 0
        files = sorted(os.listdir(self.ACTIONS_DIR))
        for filename in files:
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            mod_name = filename[:-3]
            try:
                module = importlib.import_module(f"{self.ACTIONS_DIR}.{mod_name}")
                importlib.reload(module)
                if hasattr(module, "ACTION_INFO") and hasattr(module, "run"):
                    action_id = module.ACTION_INFO.get("id")
                    priority = module.ACTION_INFO.get("priority", 99)
                    is_block = (
                        "Yes" if module.ACTION_INFO.get("is_blocking", False) else "No"
                    )
                    if action_id:
                        self._actions[action_id] = module
                        print(
                            f" ✅ [{priority:02d}] {action_id:<18} | Block: {is_block}"
                        )
                        loaded_count += 1
            except Exception as ex:
                print(f" ❌ [Error] {mod_name}: {ex}")
        print("-" * 50)
        print(f"🚀 Total Actions Loaded: {loaded_count}")
        print("=" * 50 + "\n")

    def _init_hardware(self):
        try:
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self._joystick = pygame.joystick.Joystick(0)
                self._joystick.init()
                print(f"🎮 Hardware Ready: {self._joystick.get_name()}")
            else:
                self._joystick = None
        except Exception as ex:
            print(f"❌ Hardware Error: {ex}")

    def _init_virtual_device(self):
        keys = [
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
            e.KEY_1,
            e.KEY_2,
            e.KEY_3,
            e.KEY_4,
            e.KEY_5,
            e.KEY_6,
            e.KEY_7,
            e.KEY_8,
            e.KEY_9,
            e.KEY_0,
            e.KEY_SPACE,
            e.KEY_ENTER,
            e.KEY_ESC,
            e.KEY_BACKSPACE,
            e.KEY_LEFTSHIFT,
            e.KEY_LEFTCTRL,
            e.KEY_LEFTALT,
            e.KEY_PLAYPAUSE,
            e.KEY_NEXTSONG,
            e.KEY_PREVIOUSSONG,
            e.KEY_MUTE,
            e.KEY_VOLUMEUP,
            e.KEY_VOLUMEDOWN,
            e.BTN_LEFT,
            e.BTN_RIGHT,
            e.BTN_MIDDLE,
        ]
        try:
            self._ui_virtual = UInput(
                {e.EV_REL: (e.REL_X, e.REL_Y, e.REL_WHEEL), e.EV_KEY: keys},
                name="JoyConMe",
            )
        except:
            print("❌ UInput Fail (Need sudo/udev rules)")

    def get_sleep_time(self):
        rate = self._app_config.get("system", {}).get(
            "tick_rate", self.DEFAULT_TICK_RATE
        )
        return 1.0 / max(1, rate)

    def run_tick(self):
        if not pygame.get_init():
            return "EXIT"
        if self._joystick is None:
            if pygame.joystick.get_count() > 0:
                self._init_hardware()
            return

        pygame.event.pump()
        is_shield_active = self._app_config.get("system", {}).get(
            "action_shield", False
        )

        # 🎯 เรียงลำดับ Action ตาม Priority
        sorted_actions = sorted(
            self._actions.items(), key=lambda x: x[1].ACTION_INFO.get("priority", 99)
        )

        for action_id, module in sorted_actions:
            is_blocking_mod = module.ACTION_INFO.get("is_blocking", False)

            # --- 🛡️ Shield Check ---
            if is_shield_active and not is_blocking_mod:
                continue

            # 🚀 รัน Action
            result = self._run_action(action_id, module)

            # --- ⚠️ สัญญาณพิเศษ (Signals) ---
            if result == "EXIT":
                return "EXIT"

            if result == "SAVE_CONFIG":
                self.save_app_config()

            if result == "SAVE_MAPPING":
                self.reload_mapping_from_disk()
                # ✨ สำคัญ: เมื่อมีการเปลี่ยน Mapping (Profile) ให้หยุดการทำงานในเฟรมนี้ทันที
                # เพื่อป้องกันปุ่มเก่าค้าง หรือการส่งสัญญาณซ้ำซ้อน
                break

            # --- 🛑 Auto-Blocking ---
            # ปรับให้ยืดหยุ่น: ถ้าคืนค่า True หรือคืนค่าเป็น String สัญญาณพิเศษ ให้หยุดลูป Action เฟรมนี้
            if result is True or isinstance(result, str):
                break

    def _run_action(self, action_id, module):
        # 🚨 ดึงข้อมูลจากแรมชุดล่าสุดเสมอ
        active_prof = self._mod_mapping.get("active_profile", "default")
        prof_data = self._mod_mapping.get("profiles", {}).get(active_prof, {})

        # ดึง Mapping ตาม Profile (ถ้าไม่มีให้ว่างไว้)
        mapping = prof_data.get(action_id, {})

        try:
            return module.run(
                self._ui_virtual, self._joystick, self._app_config, mapping
            )
        except Exception as e:
            return None

    def cleanup(self):
        if self._ui_virtual:
            self._ui_virtual.close()
        pygame.quit()
        print("👋 Engine ปิดตัวเรียบร้อย")
