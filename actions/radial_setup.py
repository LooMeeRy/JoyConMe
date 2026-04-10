# actions/radial_setup.py
import importlib
import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pygame

try:
    from ui.overlay_ui import RadialMenuOverlay
except ImportError:
    RadialMenuOverlay = None

try:
    from menus.utils import format_button_name, get_emoji
except ImportError:
    from utils import format_button_name, get_emoji

# Import เฉพาะ main_menu เป็น Registry (ไม่ต้อง Import เมนูย่อยอื่นๆ แล้ว)
try:
    from menus import main_menu
except ImportError:
    main_menu = None

ACTION_INFO = {
    "id": "radial_setup",
    "name": "ระบบตั้งค่าเมนูวงกลม",
    "actions": [{"key": "open_menu", "type": "button", "desc": "เปิด/ปิด เมนูวงกลม"}],
}


@dataclass
class RadialState:
    is_active: bool = False
    current_menu_id: str = "main"
    wait_for_neutral: bool = False
    listen_mode: Optional[str] = None

    last_detected_inputs: List[Any] = field(default_factory=list)
    reference_inputs: List[Any] = field(default_factory=list)
    last_input_time: float = 0.0
    has_started_sequence: bool = False

    is_holding: bool = False
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
        if isinstance(mapping_value, dict) and "hat" in mapping_value:
            try:
                h_id = mapping_value["hat"]
                target_dir = mapping_value["dir"]
                current_val = joystick.get_hat(h_id)
                if target_dir[0] != 0 and current_val[0] == target_dir[0]:
                    return True
                if target_dir[1] != 0 and current_val[1] == target_dir[1]:
                    return True
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
        except:
            pass
        try:
            for h in range(joystick.get_numhats()):
                val = joystick.get_hat(h)
                if val != (0, 0):
                    inputs.append({"hat": h, "dir": list(val)})
        except:
            pass
        if include_analog:
            try:
                for a in range(joystick.get_numaxes()):
                    val = joystick.get_axis(a)
                    if abs(val) > 0.85:
                        inputs.append(a)
            except:
                pass
        return inputs

    def open_menu(self):
        # สแกนเมนูใหม่แบบ Plug & Play ทันทีทุกครั้งที่เปิดเมนูขึ้นมา
        if main_menu:
            main_menu.reload_menus()

        self.state.is_active = True
        self.state.current_menu_id = "main"
        self.state.wait_for_neutral = True
        self.state.listen_mode = None

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
            magnitude = math.sqrt(axis_x**2 + axis_y**2)
            if magnitude > 0.4:
                angle = (math.degrees(math.atan2(axis_y, axis_x)) + 90) % 360
                self.state.overlay_window.update_selection(angle)
        except:
            pass

    def handle_menu_selection(self, joystick, app_config) -> Optional[str]:
        if not self.state.overlay_window:
            return None
        try:
            selected_idx = self.state.overlay_window.current_selection
            selected_item = self.state.overlay_window.menu_items[selected_idx]
        except (IndexError, AttributeError):
            return None

        context = {
            "overlay": self.state.overlay_window,
            "joystick": joystick,
            "app_config": app_config,
        }

        # ใช้ Dynamic Registry แทน Hardcode
        result = None
        if main_menu:
            menu_handler = main_menu.get_menu_module(self.state.current_menu_id)
            if menu_handler and hasattr(menu_handler, "run"):
                result = menu_handler.run(selected_item, context)
        return result

    def process_listen_mode(self, joystick) -> bool:
        if self.state.listen_mode is None:
            return False

        current_inputs = self.get_current_physical_inputs(
            joystick, include_analog=False
        )
        overlay = self.state.overlay_window
        if not overlay:
            return False

        if self.state.wait_for_neutral:
            buttons_only = self.get_current_physical_inputs(
                joystick, include_analog=False
            )
            if len(buttons_only) > 0:
                overlay.center_msg = "กรุณาปล่อยทุกปุ่มก่อน..."
            else:
                self.state.wait_for_neutral = False
                self.state.reference_inputs = []
                self.state.last_detected_inputs = []
                self.state.is_holding = False
                self.state.last_input_time = time.time()
                self.state.has_started_sequence = False
                overlay.center_msg = "พร้อมแล้ว!\n(กดปุ่มได้เลย)"
            return True

        has_any_input = len(current_inputs) > 0

        if has_any_input and not self.state.is_holding:
            self.state.is_holding = True
            self.state.last_input_time = time.time()
            self.state.has_started_sequence = True
            self.state.last_detected_inputs = current_inputs[:]

            parts = []
            for inp in current_inputs:
                if isinstance(inp, int):
                    parts.append(f"{inp}️⃣")
                elif isinstance(inp, dict):
                    parts.append(get_emoji(inp))
            overlay.center_msg = f"กดอยู่:\n{' + '.join(parts)}"
            overlay.timeout_progress = 0.0

        elif has_any_input and self.state.is_holding:
            self.state.last_detected_inputs = current_inputs[:]
            self.state.last_input_time = time.time()
            parts = []
            for inp in current_inputs:
                if isinstance(inp, int):
                    parts.append(f"{inp}️⃣")
                elif isinstance(inp, dict):
                    parts.append(get_emoji(inp))
            overlay.center_msg = f"กดอยู่:\n{' + '.join(parts)}"

        elif not has_any_input and self.state.is_holding:
            self.state.is_holding = False
            final_inputs = self.state.last_detected_inputs

            if final_inputs:
                final_val = (
                    final_inputs[0] if len(final_inputs) == 1 else final_inputs[:]
                )

                active_menu = None
                if main_menu:
                    active_menu = main_menu.get_menu_module(self.state.current_menu_id)

                if self.state.listen_mode == "input" and active_menu:
                    if hasattr(active_menu, "set_detected_input"):
                        active_menu.set_detected_input(final_val)
                    if hasattr(active_menu, "proceed_after_input"):
                        result = active_menu.proceed_after_input({"overlay": overlay})
                        if result == "UPDATE_UI":
                            self.state.listen_mode = None
                            self.state.last_detected_inputs = []
                            return True

                elif self.state.listen_mode == "sequence" and active_menu:
                    if (
                        hasattr(active_menu, "is_recording")
                        and active_menu.is_recording
                    ):
                        if hasattr(active_menu, "add_sequence_input"):
                            active_menu.add_sequence_input(
                                final_val, {"overlay": overlay}
                            )

                self.state.last_detected_inputs = []

        else:
            if self.state.listen_mode == "sequence" and self.state.has_started_sequence:
                elapsed = time.time() - self.state.last_input_time
                if elapsed > self.state.GRACE_PERIOD:
                    progress = (
                        elapsed - self.state.GRACE_PERIOD
                    ) / self.state.TIMEOUT_SECONDS
                    overlay.timeout_progress = min(progress, 1.0)
                    secs_left = int(
                        self.state.TIMEOUT_SECONDS - (elapsed - self.state.GRACE_PERIOD)
                    )
                    overlay.center_msg = f"หยุดบันทึกใน\n{secs_left} วินาที..."

                    if progress >= 1.0:
                        if main_menu:
                            active_menu = main_menu.get_menu_module(
                                self.state.current_menu_id
                            )
                            if active_menu and hasattr(active_menu, "is_recording"):
                                active_menu.is_recording = False

                        self.state.has_started_sequence = False
                        overlay.timeout_progress = 0.0
                        overlay.center_msg = "หยุดบันทึกแล้ว\nเลือกเมนูด้านล่าง"
                        self.state.wait_for_neutral = True
                        self.state.listen_mode = None

        return True

    def run(
        self, ui_virtual, joystick, app_config, mod_mapping, trigger_key=None
    ) -> Optional[str]:
        if trigger_key == "open_menu":
            self.open_menu()
            return True

        if not joystick:
            return False

        trigger_config = mod_mapping.get("buttons", {}).get("open_menu")
        btn_pressed = self.is_combo_pressed(joystick, trigger_config)
        is_just_pressed = btn_pressed and not self.state.last_btn_state
        self.state.last_btn_state = btn_pressed

        if is_just_pressed:
            if self.state.is_active:
                self.close_menu()
                return "RELOAD"
            else:
                self.open_menu()

        if not self.state.is_active or not self.state.overlay_window:
            return False

        if self.state.listen_mode is not None:
            result = self.process_listen_mode(joystick)
            self.state.overlay_window.update()
            return result

        if self.state.wait_for_neutral:
            if not joystick.get_button(0):
                self.state.wait_for_neutral = False
            self.state.overlay_window.update()
            return True

        self.update_selection_from_axis(joystick)

        # กดปุ่ม A → เลือก
        if joystick.get_button(0):
            result = self.handle_menu_selection(joystick, app_config)

            if result == "CLOSE_MENU":
                self.close_menu()
                return "RELOAD"

            elif isinstance(result, str) and result.startswith("SWITCH:"):
                target = result.split(":")[1]
                self.state.current_menu_id = target
                self.state.wait_for_neutral = True

                # Dynamic Switch Menu
                if main_menu:
                    active_menu = main_menu.get_menu_module(target)
                    if active_menu:
                        if hasattr(active_menu, "reset"):
                            active_menu.reset()

                        # รองรับได้ทั้ง MENU_MAIN และ MENU_ITEMS
                        if hasattr(active_menu, "MENU_MAIN"):
                            self.state.overlay_window.menu_items = active_menu.MENU_MAIN
                        elif hasattr(active_menu, "MENU_ITEMS"):
                            self.state.overlay_window.menu_items = (
                                active_menu.MENU_ITEMS
                            )
                        else:
                            self.state.overlay_window.menu_items = ["ไม่มีเมนู"]

                self.state.overlay_window.center_msg = ""

            elif result == "LISTEN_INPUT":
                self.state.listen_mode = "input"
                self.state.wait_for_neutral = True
                self.state.last_detected_inputs = []
                self.state.is_holding = False
                self.state.overlay_window.menu_items = ["(รอสัญญาณ)"]
                self.state.overlay_window.center_msg = "กรุณาปล่อยทุกปุ่มก่อน..."

            elif result == "START_SEQUENCE_LISTEN":
                self.state.listen_mode = "sequence"
                self.state.wait_for_neutral = True
                self.state.last_detected_inputs = []
                self.state.is_holding = False
                self.state.last_input_time = time.time()
                self.state.has_started_sequence = False

            elif result == "STOP_SEQUENCE_LISTEN":
                self.state.listen_mode = None
                self.state.wait_for_neutral = True

            elif result == "UPDATE_UI":
                self.state.wait_for_neutral = True

            pygame.time.wait(250)

        self.state.overlay_window.update()
        return True


_controller = RadialMenuController()


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    return _controller.run(ui_virtual, joystick, app_config, mod_mapping, trigger_key)
