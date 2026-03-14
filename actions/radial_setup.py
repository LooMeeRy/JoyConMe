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

try:
    from menus import button_menu, cheat_menu, main_menu, mouse_menu
except ImportError:
    button_menu = None
    cheat_menu = None
    main_menu = None
    mouse_menu = None


ACTION_INFO = {
    "id": "radial_setup",
    "name": "ระบบตั้งค่าเมนูวงกลม",
    "actions": [{"key": "open_menu", "type": "button", "desc": "เปิด/ปิด เมนูวงกลม"}],
}


@dataclass
class RadialState:
    """เก็บ State ของ Radial Menu แทนการใช้ Global Variable"""

    is_active: bool = False
    current_menu_id: str = "main"
    wait_for_neutral: bool = False
    listen_mode: Optional[str] = None  # "input" หรือ "sequence"

    # Input detection state
    last_detected_inputs: List[Any] = field(default_factory=list)
    reference_inputs: List[Any] = field(default_factory=list)
    last_input_time: float = 0.0
    has_started_sequence: bool = False

    # UI
    overlay_window: Optional[Any] = None
    last_btn_state: bool = False

    # Constants
    GRACE_PERIOD: float = 0.5
    TIMEOUT_SECONDS: float = 5.0


class RadialMenuController:
    """Controller สำหรับจัดการ Radial Menu"""

    def __init__(self):
        self.state = RadialState()
        self._menus = {
            "main": main_menu,
            "mouse_main": mouse_menu,
            "button_main": button_menu,
            "cheat_main": cheat_menu,
        }

    def is_combo_pressed(self, joystick, mapping_value) -> bool:
        """ตรวจสอบการกดปุ่มแบบ Combo"""
        if mapping_value is None:
            return False

        # Case 1: ปุ่มธรรมดา
        if isinstance(mapping_value, int):
            try:
                return joystick.get_button(mapping_value)
            except:
                return False

        # Case 2: List (Combo)
        if isinstance(mapping_value, list):
            return all(self.is_combo_pressed(joystick, item) for item in mapping_value)

        # Case 3: Dict (Hat/D-pad)
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
        """อ่านค่า input ปัจจุบันจากจอย"""
        inputs = []

        # Buttons
        try:
            for i in range(joystick.get_numbuttons()):
                if joystick.get_button(i):
                    inputs.append(i)
        except:
            pass

        # Hats
        try:
            for h in range(joystick.get_numhats()):
                val = joystick.get_hat(h)
                if val != (0, 0):
                    inputs.append({"hat": h, "dir": list(val)})
        except:
            pass

        # Analog (ถ้าเปิดใช้งาน)
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
        """เปิดเมนูวงกลม"""
        self.state.is_active = True
        self.state.current_menu_id = "main"
        self.state.wait_for_neutral = True
        self.state.listen_mode = None

        if RadialMenuOverlay and not self.state.overlay_window:
            items = main_menu.MENU_ITEMS if main_menu else ["Error"]
            self.state.overlay_window = RadialMenuOverlay(menu_items=items)
            self.state.overlay_window.show()

    def close_menu(self):
        """ปิดเมนูวงกลม"""
        self.state.is_active = False
        if self.state.overlay_window:
            self.state.overlay_window.close()
            self.state.overlay_window = None

    def update_selection_from_axis(self, joystick):
        """อัปเดตการเลือกเมนูจาก Analog Stick"""
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
        """จัดการเมื่อผู้ใช้เลือกเมนู"""
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

        result = None
        menu_handler = self._menus.get(self.state.current_menu_id)

        if menu_handler and hasattr(menu_handler, "run"):
            result = menu_handler.run(selected_item, context)

        return result

    def process_listen_mode(self, joystick) -> bool:
        """จัดการโหมดรอ Input (ตั้งค่าปุ่มหรือบันทึกสูตร)"""
        if self.state.listen_mode is None:
            return False

        # ตรวจจับ Analog เฉพาะโหมด input (ไม่ใช่ sequence)
        detect_analog = self.state.listen_mode == "input"
        current_inputs = self.get_current_physical_inputs(
            joystick, include_analog=detect_analog
        )

        overlay = self.state.overlay_window
        if not overlay:
            return False

        # รอให้ปล่อยปุ่มก่อน
        if self.state.wait_for_neutral:
            if 0 in current_inputs:  # ปุ่ม A ยังกดอยู่
                overlay.center_msg = "รอปล่อยปุ่ม A..."
                overlay.timeout_progress = 0.0
            else:
                self.state.wait_for_neutral = False
                self.state.reference_inputs = current_inputs
                self.state.last_detected_inputs = []
                self.state.last_input_time = time.time()
                self.state.has_started_sequence = False
                overlay.center_msg = "พร้อมรับสัญญาณ\n(กดปุ่มใหม่ได้เลย)"
            return True

        # ตรวจจับ Input ใหม่
        new_inputs = [x for x in current_inputs if x not in self.state.reference_inputs]

        if new_inputs:
            self.state.last_input_time = time.time()
            overlay.timeout_progress = 0.0
            self.state.has_started_sequence = True

            # แสดงผลปุ่มที่กด
            parts = []
            for inp in new_inputs:
                if isinstance(inp, int):
                    parts.append(f"{inp}️⃣")
                elif isinstance(inp, dict):
                    parts.append(get_emoji(inp))

            overlay.center_msg = f"กดอยู่:\n{' + '.join(parts)}"
            self.state.last_detected_inputs = new_inputs

        elif self.state.last_detected_inputs:
            # ปล่อยปุ่มแล้ว → บันทึกค่า
            final_val = (
                self.state.last_detected_inputs[0]
                if len(self.state.last_detected_inputs) == 1
                else self.state.last_detected_inputs
            )

            if self.state.listen_mode == "input" and button_menu:
                button_menu.set_detected_input(final_val)
                result = button_menu.proceed_after_input({"overlay": overlay})
                if result == "UPDATE_UI":
                    self.state.listen_mode = None
                    self.state.last_detected_inputs = []
                    return True

            elif self.state.listen_mode == "sequence" and cheat_menu:
                if cheat_menu.is_recording:
                    cheat_menu.add_sequence_input(final_val, {"overlay": overlay})

            self.state.last_detected_inputs = []

        else:
            # Check timeout
            elapsed = time.time() - self.state.last_input_time
            if self.state.has_started_sequence and elapsed > self.state.GRACE_PERIOD:
                progress = (
                    elapsed - self.state.GRACE_PERIOD
                ) / self.state.TIMEOUT_SECONDS
                overlay.timeout_progress = min(progress, 1.0)
                secs_left = int(
                    self.state.TIMEOUT_SECONDS - (elapsed - self.state.GRACE_PERIOD)
                )
                overlay.center_msg = f"หยุดบันทึกใน\n{secs_left} วินาที..."

                if progress >= 1.0 and cheat_menu:
                    cheat_menu.is_recording = False
                    self.state.has_started_sequence = False
                    overlay.timeout_progress = 0.0
                    overlay.center_msg = "หยุดบันทึกแล้ว\nเลือกเมนูด้านล่าง"
                    self.state.wait_for_neutral = True
                    self.state.listen_mode = None

        return True

    def run(
        self, ui_virtual, joystick, app_config, mod_mapping, trigger_key=None
    ) -> Optional[str]:
        """
        Main entry point สำหรับ Radial Menu

        Returns:
            "RELOAD" - ต้องการโหลด Config ใหม่
            True - กิน input นี้แล้ว (ไม่ส่งต่อ Action อื่น)
            False/None - ไม่ได้ทำอะไร
        """
        # Trigger Mode (จากสูตรลับ)
        if trigger_key == "open_menu":
            self.open_menu()
            return True

        # Normal Mode
        if not joystick:
            return False

        # ตรวจจับการเปิด/ปิดเมนู
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

        if not self.state.is_active:
            return False

        # เมนูกำลังแสดงอยู่
        if not self.state.overlay_window:
            return False

        # โหมดรอ Input (ตั้งค่าปุ่ม/บันทึกสูตร)
        if self.state.listen_mode is not None:
            result = self.process_listen_mode(joystick)
            self.state.overlay_window.update()  # ✨ เพิ่มบรรทัดนี้เพื่อให้ UI ขยับ
            return result

        # รอให้ปล่อยปุ่ม A ก่อน (debounce)
        if self.state.wait_for_neutral:
            if not joystick.get_button(0):
                self.state.wait_for_neutral = False
            self.state.overlay_window.update()  # ✨ เพิ่มบรรทัดนี้ด้วยเช่นกัน
            return True

        # อัปเดตการเลือกจาก Analog
        self.update_selection_from_axis(joystick)

        # ตรวจจับการกดปุ่ม A (เลือก)
        if joystick.get_button(0):
            result = self.handle_menu_selection(joystick, app_config)

            if result == "CLOSE_MENU":
                self.close_menu()
                return "RELOAD"

            elif isinstance(result, str) and result.startswith("SWITCH:"):
                target = result.split(":")[1]
                self.state.current_menu_id = target
                self.state.wait_for_neutral = True

                # เปลี่ยนเมนู
                if target == "main" and main_menu:
                    self.state.overlay_window.menu_items = main_menu.MENU_ITEMS
                elif target == "mouse_main" and mouse_menu:
                    self.state.overlay_window.menu_items = mouse_menu.MENU_ITEMS
                elif target == "button_main" and button_menu:
                    button_menu.reset()
                    self.state.overlay_window.menu_items = button_menu.MENU_MAIN
                elif target == "cheat_main" and cheat_menu:
                    cheat_menu.reset()
                    self.state.overlay_window.menu_items = cheat_menu.MENU_MAIN

                self.state.overlay_window.center_msg = ""

            elif result == "LISTEN_INPUT":
                self.state.listen_mode = "input"
                self.state.wait_for_neutral = True
                self.state.reference_inputs = self.get_current_physical_inputs(
                    joystick, include_analog=True
                )
                self.state.last_detected_inputs = []
                self.state.overlay_window.menu_items = ["(รอสัญญาณ)"]
                self.state.overlay_window.center_msg = "รอปล่อยปุ่ม A..."

            elif result == "START_SEQUENCE_LISTEN":
                self.state.listen_mode = "sequence"
                self.state.wait_for_neutral = True
                self.state.reference_inputs = self.get_current_physical_inputs(joystick)
                self.state.last_detected_inputs = []
                self.state.last_input_time = time.time()
                self.state.has_started_sequence = False

            elif result == "STOP_SEQUENCE_LISTEN":
                self.state.listen_mode = None
                self.state.wait_for_neutral = True

            elif result == "UPDATE_UI":
                self.state.wait_for_neutral = True

            pygame.time.wait(250)  # Debounce

        self.state.overlay_window.update()
        return True


# Global instance (เพื่อให้ compatible กับระบบเดิม)
_controller = RadialMenuController()


# ฟังก์ชัน run แบบเดิม (สำหรับ Action System)
def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    return _controller.run(ui_virtual, joystick, app_config, mod_mapping, trigger_key)
