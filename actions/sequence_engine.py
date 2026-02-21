import importlib
import json
import os
import time

import pygame

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

ACTION_INFO = {
    "id": "sequence_engine",
    "name": "ระบบสูตรลับ",
    "actions": [
        {"key": "open_listener", "type": "button", "desc": "เปิดรับสูตร (Cheat Mode)"}
    ],
}

# --- Settings ---
RECIPE_PATH = os.path.join("config", "recipes.json")
TIMEOUT_SECONDS = 2.0

# --- Global State ---
sequence_ui_window = None
input_buffer = []
last_input_time = 0
is_active = False

# State สำหรับ Logic
reference_inputs = []
feedback_mode = None
feedback_start_time = 0
current_recipe_data = None


# --- Helper Functions ---
def get_recipes():
    if not os.path.exists(RECIPE_PATH):
        return []
    try:
        with open(RECIPE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def get_emoji(val):
    if isinstance(val, dict) and "hat" in val:
        d = val["dir"]
        if d[1] == 1:
            return "⬆️"
        if d[1] == -1:
            return "⬇️"
        if d[0] == -1:
            return "⬅️"
        if d[0] == 1:
            return "➡️"
    if isinstance(val, int):
        return f"{val}️⃣"
    if isinstance(val, list):
        return "".join([get_emoji(v) for v in val])
    return "❓"


def normalize_input(val):
    if isinstance(val, dict) and "hat" in val:
        d = val["dir"]
        if isinstance(d, tuple):
            return {"hat": val["hat"], "dir": list(d)}
        return val
    return val


def get_current_physical_inputs(joystick):
    inputs = []
    for i in range(joystick.get_numbuttons()):
        if joystick.get_button(i):
            inputs.append(i)
    for h in range(joystick.get_numhats()):
        val = joystick.get_hat(h)
        if val != (0, 0):
            inputs.append({"hat": h, "dir": list(val)})
    return inputs


def init_ui():
    global sequence_ui_window
    if not QT_AVAILABLE:
        return
    app = QApplication.instance()
    if not app:
        return

    sequence_ui_window = QWidget()
    sequence_ui_window.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
    )
    sequence_ui_window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    label = QLabel("🎮", sequence_ui_window)
    label.setObjectName("seqLabel")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    font = QFont("Segoe UI Emoji", 16, QFont.Weight.Bold)
    label.setFont(font)
    label.setStyleSheet(
        "QLabel#seqLabel { background-color: rgba(0, 0, 0, 200); color: #FFFFFF; padding: 15px 25px; border-radius: 10px; border: 2px solid #444; }"
    )

    layout = QVBoxLayout(sequence_ui_window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(label)
    sequence_ui_window.setLayout(layout)
    sequence_ui_window.hide()


def show_sequence_ui(text):
    global sequence_ui_window
    if not sequence_ui_window:
        init_ui()
    if sequence_ui_window:
        label = sequence_ui_window.findChild(QLabel, "seqLabel")
        if label:
            label.setText(text)
        sequence_ui_window.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        w, h = sequence_ui_window.width(), sequence_ui_window.height()
        sequence_ui_window.move(
            (screen.width() - w) // 2, (screen.height() - h) // 2 - 100
        )
        sequence_ui_window.show()
        sequence_ui_window.raise_()


def hide_sequence_ui():
    global sequence_ui_window
    if sequence_ui_window:
        sequence_ui_window.hide()


# ✨ Plugin Execution Logic
def execute_action_plugin(ui_virtual, action_data):
    if not action_data:
        return
    mod = action_data.get("mod")
    key = action_data.get("key")
    label = action_data.get("label", "Unknown")

    print(f"[Sequence] Triggering via run(): {label} (Mod: {mod})")

    try:
        module = importlib.import_module(f"actions.{mod}")

        # ✨ ตรวจสอบว่าฟังก์ชัน run รองรับ trigger_key ไหม
        # เราจะส่ง parameter ชื่อ 'trigger_key' เข้าไป
        # แต่เพื่อความปลอดภัย ต้องจัดการ parameter ให้ดี

        # ดึง module instance มา (ถ้ามี)
        # หรือเรียกฟังก์ชัน run ตรงๆ

        # เรียก run(..., trigger_key=key)
        # โดย ui_virtual, joystick, app_config, mod_mapping ไม่จำเป็นต้องมีใน sequence event
        # แต่ ui_virtual จำเป็นสำหรับการคลิกเมาส์

        # เราจะส่งแค่ ui_virtual กับ trigger_key
        # แต่ run ปกติรับ (ui, joy, app, mapping)
        # เราเลยต้องส่ง parameter แบบ keyword argument

        module.run(
            ui_virtual=ui_virtual,
            joystick=None,
            app_config=None,
            mod_mapping=None,
            trigger_key=key,  # <--- ตัวนี้คือสัญญาณบอกว่า "Trigger เลย"
        )

    except Exception as ex:
        print(f"[Sequence] Error executing {mod}: {ex}")


# --- Main Logic ---
def run(ui_virtual, joystick, app_config, mod_mapping):
    global input_buffer, last_input_time, is_active
    global feedback_mode, feedback_start_time, current_recipe_data, reference_inputs

    current_time = time.time()

    # PHASE 1: Feedback Display
    if feedback_mode is not None:
        elapsed = current_time - feedback_start_time

        if feedback_mode == "success":
            if elapsed < 1.0:
                return True
            else:
                if current_recipe_data:
                    execute_action_plugin(ui_virtual, current_recipe_data.get("action"))
                feedback_mode = None
                current_recipe_data = None
                hide_sequence_ui()
                input_buffer.clear()
                is_active = False
            return True

        if feedback_mode == "fail":
            if elapsed < 1.0:
                return True
            else:
                feedback_mode = None
                hide_sequence_ui()
                input_buffer.clear()
                is_active = False
            return True

    # PHASE 2: Timeout Logic
    if is_active and (current_time - last_input_time > TIMEOUT_SECONDS):
        if len(input_buffer) > 0:
            match_found = False
            recipes = get_recipes()

            for recipe in recipes:
                req = recipe.get("sequence", [])
                if len(input_buffer) >= len(req):
                    current_seq = input_buffer[-len(req) :]
                    norm_req = [normalize_input(x) for x in req]
                    norm_seq = [normalize_input(x) for x in current_seq]

                    if norm_seq == norm_req:
                        match_found = True
                        current_recipe_data = recipe
                        feedback_mode = "success"
                        feedback_start_time = current_time
                        action_label = recipe.get("name", "Success")
                        show_sequence_ui(f"✅ ถูกต้อง!\n{action_label}\n(รอสักครู่...)")
                        input_buffer.clear()
                        return True

            if not match_found:
                feedback_mode = "fail"
                feedback_start_time = current_time
                show_sequence_ui("❌ ไม่ตรงกับสูตรไหนเลย\n(รอสักครู่...)")
                input_buffer.clear()
                return True
        else:
            hide_sequence_ui()
            is_active = False
            return False

    # PHASE 3: Trigger
    trigger_val = mod_mapping.get("buttons", {}).get("open_listener")

    triggered = False
    if trigger_val is not None:
        if isinstance(trigger_val, int) and joystick.get_button(trigger_val):
            triggered = True
        elif isinstance(trigger_val, list) and all(
            joystick.get_button(b) for b in trigger_val
        ):
            triggered = True

    if triggered and not is_active:
        is_active = True
        input_buffer.clear()
        last_input_time = current_time
        reference_inputs = get_current_physical_inputs(joystick)
        show_sequence_ui("🎮 พิมพ์สูตรเลย...")
        return True

    # PHASE 4: Input Listening
    if is_active:
        current_inputs = get_current_physical_inputs(joystick)
        new_inputs = [x for x in current_inputs if x not in reference_inputs]

        released_inputs = [x for x in reference_inputs if x not in current_inputs]
        for r in released_inputs:
            if r in reference_inputs:
                reference_inputs.remove(r)

        if new_inputs:
            input_to_add = new_inputs[0] if len(new_inputs) == 1 else new_inputs
            last_input_time = current_time
            norm_input = normalize_input(input_to_add)
            input_buffer.append(norm_input)

            seq_str = "".join([get_emoji(x) for x in input_buffer])
            show_sequence_ui(seq_str)

            for n in new_inputs:
                if n not in reference_inputs:
                    reference_inputs.append(n)

        return True

    return False
