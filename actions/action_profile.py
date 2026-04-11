import json
import time

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

ACTION_INFO = {
    "id": "action_profile",
    "name": "ระบบจัดการโปรไฟล์",
    "priority": 5,
    "actions": [
        {"key": "next_profile", "type": "button", "desc": "สลับโปรไฟล์ถัดไป"},
        {"key": "prev_profile", "type": "button", "desc": "สลับโปรไฟล์ก่อนหน้า"},
    ],
}

_last_switch_time = 0
_DEBOUNCE_DELAY = 0.5
_osd_window = None


def show_osd(text):
    """ฟังก์ชันแสดงแจ้งเตือนแบบ Compact (เล็กและไม่ดึงสายตา)"""
    global _osd_window
    if not QT_AVAILABLE:
        return
    app = QApplication.instance()
    if not app:
        return

    if not _osd_window:
        _osd_window = QWidget()
        _osd_window.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        _osd_window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        label = QLabel(_osd_window)
        label.setObjectName("profLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 📏 1. ลดขนาดฟอนต์ลง (จาก 18 เหลือ 12)
        label.setFont(QFont("Segoe UI Emoji", 12, QFont.Weight.Bold))

        # 🎨 2. ปรับ Style ให้จิ๋วลง แถบแคบลง และใช้สีที่ดูโปร่งแสงขึ้น
        label.setStyleSheet("""
            QLabel#profLabel {
                background-color: rgba(25, 25, 25, 180);
                color: #00BCFF;
                padding: 8px 16px;
                border-radius: 18px;
                border: 1px solid rgba(0, 188, 255, 100);
            }
        """)

        layout = QVBoxLayout(_osd_window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        _osd_window.setLayout(layout)

    label = _osd_window.findChild(QLabel, "profLabel")
    label.setText(text)
    _osd_window.adjustSize()

    # 📍 3. ย้ายตำแหน่งไปชิดขอบบน (ห่างจากขอบแค่ 80px) จะได้ไม่บังสายตาตรงกลาง
    screen = QApplication.primaryScreen().geometry()
    _osd_window.move((screen.width() - _osd_window.width()) // 2, 80)
    _osd_window.show()


def hide_osd():
    global _osd_window
    if _osd_window:
        _osd_window.hide()


def is_triggered(joystick, val):
    if val is None:
        return False
    if isinstance(val, int):
        try:
            return joystick.get_button(val)
        except:
            return False
    if isinstance(val, list):
        return all(is_triggered(joystick, item) for item in val)
    if isinstance(val, dict) and "hat" in val:
        try:
            return list(joystick.get_hat(val["hat"])) == val["dir"]
        except:
            return False
    return False


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    global _last_switch_time
    current_time = time.time()
    key = trigger_key

    # ซ่อน OSD เมื่อเวลาผ่านไป 1.2 วินาที (ลดเวลาลงเพื่อให้หายไวขึ้น)
    if (
        _osd_window
        and _osd_window.isVisible()
        and current_time - _last_switch_time > 1.2
    ):
        hide_osd()

    if key is None and joystick and mod_mapping:
        if current_time - _last_switch_time < _DEBOUNCE_DELAY:
            return False
        for act in ACTION_INFO["actions"]:
            mapping_val = mod_mapping.get("buttons", {}).get(act["key"])
            if mapping_val is not None and is_triggered(joystick, mapping_val):
                key = act["key"]
                break

    if key is None:
        return False

    import gc

    from main import JoyConEngine

    engine = next(
        (obj for obj in gc.get_objects() if isinstance(obj, JoyConEngine)), None
    )
    if not engine:
        return False

    active_prof = engine._mod_mapping.get("active_profile", "default")
    profiles = list(engine._mod_mapping.get("profiles", {}).keys())
    if len(profiles) <= 1:
        return False

    current_index = profiles.index(active_prof) if active_prof in profiles else 0
    if key == "next_profile":
        new_index = (current_index + 1) % len(profiles)
    elif key == "prev_profile":
        new_index = (current_index - 1) % len(profiles)
    else:
        return False

    new_profile = profiles[new_index]
    engine._mod_mapping["active_profile"] = new_profile
    _last_switch_time = current_time

    show_notification = app_config.get("system", {}).get("show_profile_osd", True)
    if show_notification:
        # ✨ แสดงข้อความสั้นลง
        show_osd(f"🔄 {new_profile.upper()}")

    # print(f"✨ สลับโปรไฟล์ไปที่: {new_profile}")
    return "SAVE_MAPPING"
