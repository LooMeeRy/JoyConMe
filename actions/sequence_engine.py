import importlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# --- 1. ข้อมูลพื้นฐาน Action ---
ACTION_INFO = {
    "id": "sequence_engine",
    "name": "ระบบสูตรลับ",
    "priority": 0,
    "is_blocking": True,  # ✨ Bypass Shield ได้ (ใช้เป็นมาสเตอร์คีย์)
}


# --- 2. คลาสเก็บสถานะ ---
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


# --- 3. คลาสประมวลผลหลัก ---
class SequenceEngine:
    RECIPE_PATH = os.path.join("config", "recipes.json")

    def __init__(self):
        self.state = SequenceState()
        self._ui_window = None
        # ตรวจสอบการโหลด UI เฉพาะกรณีมีหน้าจอ
        try:
            from PySide6.QtWidgets import QApplication

            if QApplication.instance():
                self._init_ui()
        except:
            pass

    def _init_ui(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

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
            "QLabel#seqLabel { background-color: rgba(0, 0, 0, 220); color: #FFFFFF; padding: 15px 25px; border-radius: 10px; border: 2px solid #555; }"
        )

        layout = QVBoxLayout(self._ui_window)
        layout.addWidget(label)
        self._ui_window.setLayout(layout)

    def _show_ui(self, text: str):
        if not self._ui_window:
            return
        from PySide6.QtWidgets import QApplication

        label = self._ui_window.findChild(
            importlib.import_module("PySide6.QtWidgets").QLabel, "seqLabel"
        )
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
                data = json.load(f)
                return data if isinstance(data, list) else data.get("recipes", [])
        except:
            return []

    def _deep_normalize(self, val):
        """จัดการแกะก้ามปู [[...]] และแปลงเป็น String เพื่อเปรียบเทียบสูตร"""
        while isinstance(val, list) and len(val) > 0:
            val = val[0]
        if isinstance(val, dict):
            return str(dict(sorted(val.items())))
        return str(val)

    def _execute_action(self, ui_virtual, joystick, app_config, action_data):
        if not action_data:
            return None
        # ✨ ใช้คีย์ "mod" ตาม JSON ของคุณ
        mod = action_data.get("mod")
        key = action_data.get("key")

        if not mod:
            return None
        try:
            module = importlib.import_module(f"actions.{mod}")
            importlib.reload(module)
            # 🚨 ส่งคืนค่า (เช่น "EXIT") ไปที่ Engine ใหญ่
            return module.run(ui_virtual, joystick, app_config, {}, trigger_key=key)
        except Exception as ex:
            print(f"❌ [Sequence] Execute Error: {ex}")
            return None

    def _process_feedback(self, current_time, ui_virtual, joystick, app_config):
        if self.state.feedback_mode is None:
            return False
        elapsed = current_time - self.state.feedback_start_time
        if elapsed < 1.0:
            return True

        res = None
        if self.state.feedback_mode == "success":
            res = self._execute_action(
                ui_virtual,
                joystick,
                app_config,
                self.state.current_recipe_data.get("action"),
            )

        self._hide_ui()
        self.state.feedback_mode = None
        self.state.is_active = False
        return res if res else True

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

    def run(self, ui_virtual, joystick, app_config, mod_mapping) -> Any:
        current_time = time.time()

        # Phase 1: จัดการหน้าจอ Feedback และส่งสัญญาณ EXIT
        res = self._process_feedback(current_time, ui_virtual, joystick, app_config)
        if res and res != True:
            return res
        if res is True:
            return True

        # Phase 2: ตรวจสอบปุ่มเปิดรับสูตร (L+R)
        trigger_val = mod_mapping.get("buttons", {}).get("open_listener", [10, 11])
        triggered = False
        try:
            if isinstance(trigger_val, int):
                triggered = joystick.get_button(trigger_val)
            else:
                triggered = all(joystick.get_button(b) for b in trigger_val)
        except:
            pass

        if triggered and not self.state.is_active:
            self.state.is_active = True
            self.state.input_buffer.clear()
            self.state.last_input_time = current_time
            self.state.reference_inputs = self._get_current_inputs(joystick)
            self._show_ui("🎮 Cheat Code Mode...")
            return True

        if not self.state.is_active:
            return False

        # Phase 3: ตรวจสอบ Timeout และเปรียบเทียบสูตร
        if current_time - self.state.last_input_time > self.state.TIMEOUT_SECONDS:
            if self.state.input_buffer:
                recipes = self._get_recipes()
                current_seq_norm = [
                    self._deep_normalize(x) for x in self.state.input_buffer
                ]

                for recipe in recipes:
                    req_seq = [
                        self._deep_normalize(x) for x in recipe.get("sequence", [])
                    ]
                    if current_seq_norm == req_seq:
                        self.state.current_recipe_data = recipe
                        self.state.feedback_mode = "success"
                        self.state.feedback_start_time = current_time
                        self._show_ui(f"✅ สำเร็จ!\n{recipe.get('name')}")
                        return True

                self.state.feedback_mode = "fail"
                self.state.feedback_start_time = current_time
                self._show_ui("❌ สูตรไม่ถูกต้อง")
                return True
            else:
                self.state.is_active = False
                self._hide_ui()
                return False

        # Phase 4: รับ Input จากจอย
        curr = self._get_current_inputs(joystick)
        new = [x for x in curr if x not in self.state.reference_inputs]
        released = [x for x in self.state.reference_inputs if x not in curr]
        for r in released:
            if r in self.state.reference_inputs:
                self.state.reference_inputs.remove(r)

        if new:
            from menus.utils import get_emoji

            self.state.last_input_time = current_time
            self.state.input_buffer.append(new[0])
            seq_str = "".join([get_emoji(x) for x in self.state.input_buffer])
            self._show_ui(seq_str)
            for n in new:
                if n not in self.state.reference_inputs:
                    self.state.reference_inputs.append(n)

        return True


# --- 4. การสร้าง Instance (ต้องอยู่ล่างสุดหลังประกาศ Class) ---
_engine_instance = SequenceEngine()


def run(ui_virtual, joystick, app_config, mod_mapping):
    return _engine_instance.run(ui_virtual, joystick, app_config, mod_mapping)
