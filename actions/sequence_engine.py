import importlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pygame

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

try:
    from menus.utils import get_emoji, normalize_input
except ImportError:
    from utils import get_emoji, normalize_input


ACTION_INFO = {
    "id": "sequence_engine",
    "name": "ระบบสูตรลับ",
    "actions": [
        {"key": "open_listener", "type": "button", "desc": "เปิดรับสูตร (Cheat Mode)"}
    ],
}


@dataclass
class SequenceState:
    """State สำหรับ Sequence Engine"""

    input_buffer: List[Any] = field(default_factory=list)
    last_input_time: float = 0.0
    is_active: bool = False
    reference_inputs: List[Any] = field(default_factory=list)

    # Feedback state
    feedback_mode: Optional[str] = None  # "success" หรือ "fail"
    feedback_start_time: float = 0.0
    current_recipe_data: Optional[Dict] = None

    # Constants
    TIMEOUT_SECONDS: float = 2.0


class SequenceEngine:
    """ระบบจัดการสูตรลับ (Cheat Codes)"""

    RECIPE_PATH = os.path.join("config", "recipes.json")

    def __init__(self):
        self.state = SequenceState()
        self._ui_window: Optional[QWidget] = None
        self._init_ui()

    def _init_ui(self):
        """สร้าง UI สำหรับแสดงสูตร"""
        if not QT_AVAILABLE:
            return

        app = QApplication.instance()
        if not app:
            return

        self._ui_window = QWidget()
        self._ui_window.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self._ui_window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        label = QLabel("🎮", self._ui_window)
        label.setObjectName("seqLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font = QFont("Segoe UI Emoji", 16, QFont.Weight.Bold)
        label.setFont(font)
        label.setStyleSheet("""
            QLabel#seqLabel {
                background-color: rgba(0, 0, 0, 200);
                color: #FFFFFF;
                padding: 15px 25px;
                border-radius: 10px;
                border: 2px solid #444;
            }
        """)

        layout = QVBoxLayout(self._ui_window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        self._ui_window.setLayout(layout)
        self._ui_window.hide()

    def _show_ui(self, text: str):
        """แสดง UI กลางจอ"""
        if not self._ui_window:
            return

        label = self._ui_window.findChild(QLabel, "seqLabel")
        if label:
            label.setText(text)

        self._ui_window.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        w, h = self._ui_window.width(), self._ui_window.height()
        self._ui_window.move(
            (screen.width() - w) // 2, (screen.height() - h) // 2 - 100
        )
        self._ui_window.show()
        self._ui_window.raise_()

    def _hide_ui(self):
        """ซ่อน UI"""
        if self._ui_window:
            self._ui_window.hide()

    def _get_recipes(self) -> List[Dict]:
        """โหลดสูตรจากไฟล์"""
        if not os.path.exists(self.RECIPE_PATH):
            return []
        try:
            with open(self.RECIPE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def _get_current_inputs(self, joystick) -> List[Any]:
        """อ่าน input ปัจจุบัน"""
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

        return inputs

    def _execute_action(self, ui_virtual, action_data: Dict):
        """รัน Action ที่ผูกกับสูตร"""
        if not action_data:
            return

        mod = action_data.get("mod")
        key = action_data.get("key")
        label = action_data.get("label", "Unknown")

        print(f"[Sequence] Triggering: {label} (Mod: {mod})")

        try:
            module = importlib.import_module(f"actions.{mod}")
            module.run(
                ui_virtual=ui_virtual,
                joystick=None,
                app_config=None,
                mod_mapping=None,
                trigger_key=key,
            )
        except Exception as ex:
            print(f"[Sequence] Error executing {mod}: {ex}")

    def _check_timeout(self, current_time: float) -> bool:
        """ตรวจสอบ timeout และ match สูตร"""
        if current_time - self.state.last_input_time <= self.state.TIMEOUT_SECONDS:
            return False

        if len(self.state.input_buffer) == 0:
            self._hide_ui()
            self.state.is_active = False
            return False

        recipes = self._get_recipes()

        for recipe in recipes:
            req = recipe.get("sequence", [])
            if len(self.state.input_buffer) < len(req):
                continue

            current_seq = self.state.input_buffer[-len(req) :]
            norm_req = [normalize_input(x) for x in req]
            norm_seq = [normalize_input(x) for x in current_seq]

            if norm_seq == norm_req:
                # Match found!
                self.state.current_recipe_data = recipe
                self.state.feedback_mode = "success"
                self.state.feedback_start_time = current_time
                action_label = recipe.get("name", "Success")
                self._show_ui(f"✅ ถูกต้อง!\n{action_label}\n(รอสักครู่...)")
                self.state.input_buffer.clear()
                return True

        # No match
        self.state.feedback_mode = "fail"
        self.state.feedback_start_time = current_time
        self._show_ui("❌ ไม่ตรงกับสูตรไหนเลย\n(รอสักครู่...)")
        self.state.input_buffer.clear()
        return True

    def _process_feedback(self, current_time: float, ui_virtual) -> bool:
        """จัดการการแสดงผล Feedback"""
        if self.state.feedback_mode is None:
            return False

        elapsed = current_time - self.state.feedback_start_time

        if self.state.feedback_mode == "success":
            if elapsed < 1.0:
                return True  # ยังแสดงอยู่

            # รัน Action
            if self.state.current_recipe_data:
                self._execute_action(
                    ui_virtual, self.state.current_recipe_data.get("action")
                )

            # Reset
            self.state.feedback_mode = None
            self.state.current_recipe_data = None
            self._hide_ui()
            self.state.input_buffer.clear()
            self.state.is_active = False
            return True

        elif self.state.feedback_mode == "fail":
            if elapsed < 1.0:
                return True  # ยังแสดงอยู่

            # Reset
            self.state.feedback_mode = None
            self._hide_ui()
            self.state.input_buffer.clear()
            self.state.is_active = False
            return True

        return False

    def _check_trigger(self, joystick, mod_mapping, current_time: float) -> bool:
        """ตรวจสอบการเปิดโหมดสูตร"""
        trigger_val = mod_mapping.get("buttons", {}).get("open_listener")
        if trigger_val is None:
            return False

        triggered = False
        try:
            if isinstance(trigger_val, int):
                triggered = joystick.get_button(trigger_val)
            elif isinstance(trigger_val, list):
                triggered = all(joystick.get_button(b) for b in trigger_val)
        except:
            pass

        if triggered and not self.state.is_active:
            self.state.is_active = True
            self.state.input_buffer.clear()
            self.state.last_input_time = current_time
            self.state.reference_inputs = self._get_current_inputs(joystick)
            self._show_ui("🎮 พิมพ์สูตรเลย...")
            return True

        return False

    def _process_input(self, joystick, current_time: float):
        """ประมวลผล input ในโหมดสูตร"""
        current_inputs = self._get_current_inputs(joystick)

        # หา input ใหม่ที่ไม่มีใน reference
        new_inputs = [x for x in current_inputs if x not in self.state.reference_inputs]

        # อัปเดต reference (ปุ่มที่ยังกดอยู่)
        released = [x for x in self.state.reference_inputs if x not in current_inputs]
        for r in released:
            if r in self.state.reference_inputs:
                self.state.reference_inputs.remove(r)

        if new_inputs:
            self.state.last_input_time = current_time

            # เลือก input แรก หรือทั้งหมดถ้าเป็น combo
            input_to_add = new_inputs[0] if len(new_inputs) == 1 else new_inputs
            norm_input = normalize_input(input_to_add)
            self.state.input_buffer.append(norm_input)

            # แสดงผล
            seq_str = "".join([get_emoji(x) for x in self.state.input_buffer])
            self._show_ui(seq_str)

            # เพิ่มเข้า reference
            for n in new_inputs:
                if n not in self.state.reference_inputs:
                    self.state.reference_inputs.append(n)

    def run(self, ui_virtual, joystick, app_config, mod_mapping) -> bool:
        """
        Main entry point

        Returns:
            True - กิน input นี้แล้ว (โหมดสูตรกำลังทำงาน)
            False - ไม่ได้ทำอะไร
        """
        current_time = time.time()

        # Phase 1: Feedback Display
        if self._process_feedback(current_time, ui_virtual):
            return True

        # Phase 2: Timeout & Match Check (ถ้า active อยู่)
        if self.state.is_active:
            if self._check_timeout(current_time):
                return True

        # Phase 3: Trigger Check (เปิดโหมด)
        if self._check_trigger(joystick, mod_mapping, current_time):
            return True

        # Phase 4: Input Listening
        if self.state.is_active:
            self._process_input(joystick, current_time)
            return True

        return False


# Global instance
_engine = SequenceEngine()


def run(ui_virtual, joystick, app_config, mod_mapping):
    return _engine.run(ui_virtual, joystick, app_config, mod_mapping)
