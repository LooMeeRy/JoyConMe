# actions/radial_setup.py
import importlib
import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pygame

# --- การนำเข้า Module ---
try:
    from ui.overlay_ui import RadialMenuOverlay
except ImportError:
    RadialMenuOverlay = None

try:
    from menus.utils import format_button_name, get_emoji
except ImportError:

    def format_button_name(x):
        return str(x)

    def get_emoji(x):
        return "🔘"


try:
    from menus import main_menu
except ImportError:
    main_menu = None

ACTION_INFO = {
    "id": "radial_setup",
    "name": "ระบบเมนูวงกลม (Advanced)",
    "priority": 1,
    "is_blocking": True,
    "actions": [{"key": "open_menu", "type": "button", "desc": "เปิด/ปิด เมนูวงกลม"}],
}


@dataclass
class RadialState:
    is_active: bool = False
    current_menu_id: str = "main"
    wait_for_neutral: bool = False
    listen_mode: Optional[str] = None
    max_combo_detected: List[Any] = field(default_factory=list)
    last_input_time: float = 0.0
    is_holding: bool = False
    has_started_sequence: bool = False
    overlay_window: Optional[Any] = None
    last_btn_state: bool = False
    GRACE_PERIOD: float = 0.5
    TIMEOUT_SECONDS: float = 5.0


class RadialMenuController:
    def __init__(self):
        self.state = RadialState()

    def is_combo_pressed(self, joystick, mapping_value) -> bool:
        if mapping_value is None:
            return False
        if isinstance(mapping_value, int):
            try:
                return joystick.get_button(mapping_value)
            except:
                return False
        if isinstance(mapping_value, list):
            return all(self.is_combo_pressed(joystick, item) for item in mapping_value)

        # ✨ เช็ครูปแบบ Dictionary (Hat และ Analog)
        if isinstance(mapping_value, dict):
            if "hat" in mapping_value:
                try:
                    h_id = mapping_value["hat"]
                    target_dir = mapping_value["dir"]
                    current_val = joystick.get_hat(h_id)
                    return (target_dir[0] != 0 and current_val[0] == target_dir[0]) or (
                        target_dir[1] != 0 and current_val[1] == target_dir[1]
                    )
                except:
                    pass
            elif "axis" in mapping_value:
                try:
                    a_id = mapping_value["axis"]
                    target_val = mapping_value["val"]
                    current_val = joystick.get_axis(a_id)
                    # ดันสุดเกิน 85% ถึงจะนับว่ากด
                    return current_val > 0.85 if target_val > 0 else current_val < -0.85
                except:
                    pass
        return False

    def get_current_physical_inputs(
        self, joystick, include_analog: bool = False
    ) -> List[Any]:
        inputs = []
        try:
            for i in range(joystick.get_numbuttons()):
                if joystick.get_button(i):
                    inputs.append(i)
            for h in range(joystick.get_numhats()):
                val = joystick.get_hat(h)
                if val != (0, 0):
                    inputs.append({"hat": h, "dir": list(val)})

            # ✨ บันทึก Analog ได้แม่นยำและกันบัค Trigger
            if include_analog:
                for a in range(joystick.get_numaxes()):
                    val = joystick.get_axis(a)
                    # ตัดปัญหา Trigger (L2/R2 แกน 4, 5) ที่ชอบค้างค่า -1.0
                    if a in [4, 5] and val < -0.5:
                        continue
                    if abs(val) > 0.85:
                        inputs.append({"axis": a, "val": 1 if val > 0 else -1})
        except:
            pass
        return inputs

    def open_menu(self):
        if main_menu:
            main_menu.reload_menus()
        self.state.is_active = True
        self.state.current_menu_id = "main"
        self.state.wait_for_neutral = True
        self.state.listen_mode = None
        self.state.max_combo_detected = []
        if RadialMenuOverlay and not self.state.overlay_window:
            items = main_menu.MENU_ITEMS if main_menu else ["Error"]
            self.state.overlay_window = RadialMenuOverlay(menu_items=items)
            self.state.overlay_window.show()

    def close_menu(self):
        self.state.is_active = False
        if self.state.overlay_window:
            self.state.overlay_window.close()
            self.state.overlay_window = None

    def update_selection_from_axis(self, joystick):
        if not self.state.overlay_window:
            return
        try:
            axis_x = joystick.get_axis(0)
            axis_y = joystick.get_axis(1)
            if math.hypot(axis_x, axis_y) > 0.4:
                angle = (math.degrees(math.atan2(axis_y, axis_x)) + 90) % 360
                self.state.overlay_window.update_selection(angle)
        except:
            pass

    def handle_menu_selection(self, joystick, app_config) -> Optional[str]:
        if not self.state.overlay_window:
            return None
        try:
            idx = self.state.overlay_window.current_selection
            item = self.state.overlay_window.menu_items[idx]
        except:
            return None

        context = {
            "overlay": self.state.overlay_window,
            "joystick": joystick,
            "app_config": app_config,
            "controller": self,
        }

        if main_menu:
            handler = main_menu.get_menu_module(self.state.current_menu_id)
            if handler and hasattr(handler, "run"):
                return handler.run(item, context)
        return None

    def process_listen_mode(self, joystick) -> bool:
        if self.state.listen_mode is None:
            return False
        overlay = self.state.overlay_window
        if not overlay:
            return False

        # ให้ดักจับแกน Analog ได้
        inputs = self.get_current_physical_inputs(joystick, include_analog=True)

        if self.state.wait_for_neutral:
            if not inputs:
                self.state.wait_for_neutral = False
                overlay.center_msg = "พร้อมบันทึก..."
            else:
                overlay.center_msg = "ปล่อยปุ่มก่อน..."
            return True

        if inputs:
            self.state.is_holding = True
            self.state.last_input_time = time.time()
            self.state.has_started_sequence = True
            for inp in inputs:
                if inp not in self.state.max_combo_detected:
                    self.state.max_combo_detected.append(inp)

            # ✨ ปรับให้แสดงชื่อแกน/ปุ่มที่ตรวจเจอได้ชัดเจน (เช่น 🕹️A4+)
            parts = []
            for i in self.state.max_combo_detected:
                if isinstance(i, dict) and "axis" in i:
                    parts.append(f"🕹️A{i['axis']}({'+' if i['val'] > 0 else '-'})")
                elif isinstance(i, dict) and "hat" in i:
                    parts.append(get_emoji(i))
                else:
                    parts.append(f"{i}️⃣")

            overlay.center_msg = f"ตรวจเจอ:\n{' + '.join(parts)}"
            overlay.timeout_progress = 0.0

        elif self.state.is_holding:
            self.state.is_holding = False
            final = self.state.max_combo_detected
            handler = (
                main_menu.get_menu_module(self.state.current_menu_id)
                if main_menu
                else None
            )

            if self.state.listen_mode == "input" and handler:
                if hasattr(handler, "set_detected_input"):
                    handler.set_detected_input(final)
                if hasattr(handler, "proceed_after_input"):
                    if handler.proceed_after_input({"overlay": overlay}) == "UPDATE_UI":
                        self.state.listen_mode = None
                        return True
            elif self.state.listen_mode == "sequence" and handler:
                if getattr(handler, "is_recording", False) and hasattr(
                    handler, "add_sequence_input"
                ):
                    handler.add_sequence_input(final, {"overlay": overlay})
            self.state.max_combo_detected = []

        # (ตัดส่วน sequence timeout เดิมออกไปเพื่อให้ดูง่ายขึ้นตามที่คุณต้องการ)
        return True

    def run(
        self, ui_virtual, joystick, app_config, mod_mapping, trigger_key=None
    ) -> Any:
        # 🟢 1. เปิดผ่าน Secret Sequence
        if trigger_key == "open_menu":
            if not self.state.is_active:
                self.open_menu()
            else:
                self.close_menu()
            return True

        if not joystick:
            return False

        # 🟢 2. เปิดผ่านปุ่มจอย
        trigger_config = mod_mapping.get("buttons", {}).get("open_menu")
        btn_pressed = self.is_combo_pressed(joystick, trigger_config)
        if btn_pressed and not self.state.last_btn_state:
            if self.state.is_active:
                self.close_menu()
            else:
                self.open_menu()
        self.state.last_btn_state = btn_pressed

        if not self.state.is_active:
            return False

        # 🟢 3. จัดการโหมด Listen
        if self.state.listen_mode:
            self.process_listen_mode(joystick)
            if self.state.overlay_window:
                self.state.overlay_window.update()
            return True

        # 🟢 4. รอให้ปล่อยปุ่มก่อนรับคำสั่งใหม่
        if self.state.wait_for_neutral:
            if not any(
                joystick.get_button(i) for i in range(joystick.get_numbuttons())
            ):
                self.state.wait_for_neutral = False

            # ✨ จุดสำคัญ: ให้ขยับเมนูได้ แม้ระบบจะรอให้ปล่อยปุ่มอยู่
            self.update_selection_from_axis(joystick)

            if self.state.overlay_window:
                self.state.overlay_window.update()
            return True

        self.update_selection_from_axis(joystick)

        # 🟢 5. ยืนยันเลือกเมนู
        if joystick.get_button(0):
            result = self.handle_menu_selection(joystick, app_config)

            if result == "CLOSE_MENU":
                self.close_menu()
                return "RELOAD"

            elif result in ["SAVE_MAPPING", "SAVE_CONFIG"]:
                self.close_menu()
                return result

            elif isinstance(result, str) and result.startswith("SWITCH:"):
                target = result.split(":")[1]
                self.state.current_menu_id = target
                self.state.wait_for_neutral = True
                if main_menu:
                    handler = main_menu.get_menu_module(target)
                    if handler:
                        if hasattr(handler, "reset"):
                            handler.reset()
                        items = getattr(
                            handler,
                            "MENU_MAIN",
                            getattr(handler, "MENU_ITEMS", ["Error"]),
                        )
                        self.state.overlay_window.menu_items = items
                self.state.overlay_window.center_msg = ""

            elif result == "LISTEN_INPUT":
                self.state.listen_mode = "input"
                self.state.wait_for_neutral = True
                self.state.overlay_window.menu_items = ["..."]
                self.state.overlay_window.center_msg = "รอสัญญาณปุ่ม/แกน..."

            pygame.time.wait(200)

        if self.state.overlay_window:
            self.state.overlay_window.update()
        return True


_controller = RadialMenuController()


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    return _controller.run(ui_virtual, joystick, app_config, mod_mapping, trigger_key)
