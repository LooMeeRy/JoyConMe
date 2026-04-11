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
    # Fallback กรณีหา Path ไม่เจอ
    def normalize_input(x):
        return x

    def get_emoji(x):
        return "❓"


ACTION_INFO = {
    "id": "sequence_engine",
    "name": "ระบบสูตรลับ",
    "priority": 99,
    "is_blocking": False,
    "actions": [
        {"key": "open_listener", "type": "button", "desc": "เปิดรับสูตร (Cheat Mode)"}
    ],
}


@dataclass
class SequenceState:
    input_buffer: List[Any] = field(default_factory=list)
    last_input_time: float = 0.0
    is_active: bool = False
    reference_inputs: List[Any] = field(default_factory=list)
    feedback_mode: Optional[str] = None
    feedback_start_time: float = 0.0
    current_recipe_data: Optional[Dict] = None
    TIMEOUT_SECONDS: float = 2.0


class SequenceEngine:
    RECIPE_PATH = os.path.join("config", "recipes.json")

    def __init__(self):
        self.state = SequenceState()
        self._ui_window: Optional[QWidget] = None
        self._init_ui()

    def _init_ui(self):
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
        label.setFont(QFont("Segoe UI Emoji", 16, QFont.Weight.Bold))
        label.setStyleSheet(
            "QLabel#seqLabel { background-color: rgba(0, 0, 0, 200); color: #FFFFFF; padding: 15px 25px; border-radius: 10px; border: 2px solid #444; }"
        )

        layout = QVBoxLayout(self._ui_window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        self._ui_window.setLayout(layout)

    def _show_ui(self, text: str):
        if not self._ui_window:
            return
        label = self._ui_window.findChild(QLabel, "seqLabel")
        if label:
            label.setText(text)
        self._ui_window.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        self._ui_window.move(
            (screen.width() - self._ui_window.width()) // 2,
            (screen.height() - self._ui_window.height()) // 2 - 100,
        )
        self._ui_window.show()

    def _hide_ui(self):
        if self._ui_window:
            self._ui_window.hide()

    def _get_recipes(self) -> List[Dict]:
        if not os.path.exists(self.RECIPE_PATH):
            return []
        try:
            with open(self.RECIPE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def _get_current_inputs(self, joystick) -> List[Any]:
        inputs = []
        try:
            for i in range(joystick.get_numbuttons()):
                if joystick.get_button(i):
                    inputs.append(i)
            for h in range(joystick.get_numhats()):
                val = joystick.get_hat(h)
                if val != (0, 0):
                    inputs.append({"hat": h, "dir": list(val)})
        except:
            pass
        return inputs

    # ✨ จุดที่แก้ไข 1: ปรับให้แกะก้ามปูซ้อน [[0]] อัตโนมัติ
    def _deep_normalize(self, val):
        while isinstance(val, list) and len(val) > 0:
            val = val[0]
        return normalize_input(val)

    # ✨ จุดที่แก้ไข 2: ส่งต่อค่าสำคัญ (joystick, app_config) ให้ Action อื่นทำงานได้จริง
    def _execute_action(self, ui_virtual, joystick, app_config, action_data: Dict):
        if not action_data:
            return None
        mod = action_data.get("mod")
        key = action_data.get("key")

        try:
            module = importlib.import_module(f"actions.{mod}")
            # ต้องส่ง joystick และ app_config ไปด้วย เพื่อให้ Shield เซฟค่าได้
            return module.run(
                ui_virtual=ui_virtual,
                joystick=joystick,
                app_config=app_config,
                mod_mapping={},
                trigger_key=key,
            )
        except Exception as ex:
            print(f"[Sequence] Error executing {mod}: {ex}")
            return None

    def _check_timeout(self, current_time: float) -> bool:
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

            # ✨ ใช้ deep_normalize เพื่อแก้ปัญหา [[0]]
            norm_req = [self._deep_normalize(x) for x in req]
            norm_seq = [self._deep_normalize(x) for x in current_seq]

            if norm_seq == norm_req:
                self.state.current_recipe_data = recipe
                self.state.feedback_mode = "success"
                self.state.feedback_start_time = current_time
                self._show_ui(
                    f"✅ ถูกต้อง!\n{recipe.get('name', 'Success')}\n(รอสักครู่...)"
                )
                self.state.input_buffer.clear()
                return True

        self.state.feedback_mode = "fail"
        self.state.feedback_start_time = current_time
        self._show_ui("❌ ไม่ตรงกับสูตรไหนเลย\n(รอสักครู่...)")
        self.state.input_buffer.clear()
        return True

    def _process_feedback(self, current_time: float, ui_virtual, joystick, app_config):
        if self.state.feedback_mode is None:
            return False
        elapsed = current_time - self.state.feedback_start_time

        if elapsed < 1.0:
            return True

        # ✨ จุดที่แก้ไข 3: รับค่าตอบกลับจาก Action (เช่น SAVE_CONFIG) เพื่อส่งต่อให้ Engine ใหญ่
        result = False
        if self.state.feedback_mode == "success" and self.state.current_recipe_data:
            result = self._execute_action(
                ui_virtual,
                joystick,
                app_config,
                self.state.current_recipe_data.get("action"),
            )

        self.state.feedback_mode = None
        self.state.current_recipe_data = None
        self._hide_ui()
        self.state.is_active = False

        # ถ้า Action ส่งค่าพิเศษมา (เช่น SAVE_CONFIG หรือ EXIT) ให้ส่งต่อไปที่ Engine ใหญ่
        return result if result else True

    def _check_trigger(self, joystick, mod_mapping, current_time: float) -> bool:
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
        current_inputs = self._get_current_inputs(joystick)
        new_inputs = [x for x in current_inputs if x not in self.state.reference_inputs]
        released = [x for x in self.state.reference_inputs if x not in current_inputs]

        for r in released:
            if r in self.state.reference_inputs:
                self.state.reference_inputs.remove(r)

        if new_inputs:
            self.state.last_input_time = current_time
            input_to_add = new_inputs[0] if len(new_inputs) == 1 else new_inputs
            self.state.input_buffer.append(self._deep_normalize(input_to_add))

            # อัปเดต UI แสดง Emoji ของปุ่มที่กดไปแล้ว
            seq_str = "".join([get_emoji(x) for x in self.state.input_buffer])
            self._show_ui(seq_str)
            for n in new_inputs:
                if n not in self.state.reference_inputs:
                    self.state.reference_inputs.append(n)

    def run(self, ui_virtual, joystick, app_config, mod_mapping) -> Any:
        current_time = time.time()

        # Phase 1: Feedback
        res = self._process_feedback(current_time, ui_virtual, joystick, app_config)
        if res:
            return res

        # Phase 2: Timeout & Match
        if self.state.is_active:
            if self._check_timeout(current_time):
                return True

        # Phase 3: Trigger Check
        if self._check_trigger(joystick, mod_mapping, current_time):
            return True

        # Phase 4: Input Listening
        if self.state.is_active:
            self._process_input(joystick, current_time)
            return True

        return False


_engine = SequenceEngine()


def run(ui_virtual, joystick, app_config, mod_mapping):
    return _engine.run(ui_virtual, joystick, app_config, mod_mapping)
