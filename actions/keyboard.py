"""
actions/keyboard.py
ระบบ Virtual Keyboard สำหรับพิมพ์ตัวอักษรด้วย Joystick

Layout กริด 3x3 (ช่องกลางว่าง):
  [ABC] [DEF] [GHI]
  [JKL] [ * ] [MNO]
  [PQS] [TUV] [WXYZ]

Controls:
  Analog ซ้าย (axis 0, 1) → เลือกช่อง
  ปุ่ม A (0)               → กดครั้งแรก = พิมพ์ตัวแรก, กดซ้ำ = วนตัวถัดไป
  ปุ่ม X (2)               → Backspace
  ปุ่ม Y (3)               → Space
  ปุ่ม B (1)               → Enter
  ปุ่ม trigger (config)    → เปิด/ปิด Keyboard
"""

import time
from typing import Optional

from evdev import ecodes as e

try:
    from ui.keyboard_ui import CHAR_GROUPS, KeyboardOverlay
except ImportError:
    KeyboardOverlay = None
    CHAR_GROUPS = [
        "ABC",
        "DEF",
        "GHI",
        "JKL",
        None,
        "MNO",
        "PQS",
        "TUV",
        "WXYZ",
    ]

# evdev keycodes สำหรับตัวอักษร a-z
_CHAR_TO_KEYCODE = {
    "a": e.KEY_A,
    "b": e.KEY_B,
    "c": e.KEY_C,
    "d": e.KEY_D,
    "e": e.KEY_E,
    "f": e.KEY_F,
    "g": e.KEY_G,
    "h": e.KEY_H,
    "i": e.KEY_I,
    "j": e.KEY_J,
    "k": e.KEY_K,
    "l": e.KEY_L,
    "m": e.KEY_M,
    "n": e.KEY_N,
    "o": e.KEY_O,
    "p": e.KEY_P,
    "q": e.KEY_Q,
    "r": e.KEY_R,
    "s": e.KEY_S,
    "t": e.KEY_T,
    "u": e.KEY_U,
    "v": e.KEY_V,
    "w": e.KEY_W,
    "x": e.KEY_X,
    "y": e.KEY_Y,
    "z": e.KEY_Z,
}

ACTION_INFO = {
    "id": "keyboard",
    "name": "คีย์บอร์ดเสมือน",
    "actions": [
        {"key": "toggle_keyboard", "type": "button", "desc": "เปิด/ปิด คีย์บอร์ด"},
    ],
}

# ค่า deadzone สำหรับ analog stick
_DEADZONE = 0.45

# เวลาขั้นต่ำระหว่างการกดปุ่ม A ซ้ำ (วินาที)
_CYCLE_DELAY = 0.25

# เวลาที่ต้องรอหลังจากปล่อยปุ่มก่อนจะถือว่า "commit" ตัวอักษร (วินาที)
_COMMIT_DELAY = 1.2


def _press_key(ui_virtual, keycode: int):
    """ส่ง key press + release ผ่าน evdev"""
    try:
        ui_virtual.write(e.EV_KEY, keycode, 1)
        ui_virtual.syn()
        time.sleep(0.02)
        ui_virtual.write(e.EV_KEY, keycode, 0)
        ui_virtual.syn()
    except Exception as ex:
        print(f"[Keyboard] key error: {ex}")


def _type_char(ui_virtual, char: str, shift: bool = False):
    """พิมพ์ตัวอักษร 1 ตัว (shift=True = พิมพ์ใหญ่)"""
    c = char.lower()
    kc = _CHAR_TO_KEYCODE.get(c)
    if kc:
        if shift:
            ui_virtual.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
            ui_virtual.syn()
        _press_key(ui_virtual, kc)
        if shift:
            ui_virtual.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
            ui_virtual.syn()


def _analog_to_cell(ax: float, ay: float) -> Optional[int]:
    """
    แปลงค่า analog stick เป็น cell index (0-8)
    ช่องกลาง (4) คือ deadzone
    คืน None ถ้าอยู่ใน deadzone
    """
    if abs(ax) < _DEADZONE and abs(ay) < _DEADZONE:
        return None  # อยู่ตรงกลาง → ช่องกลาง (ไม่เลือก)

    # ใช้มุมเพื่อแบ่ง 8 ทิศ
    import math

    angle = math.degrees(math.atan2(ay, ax))  # -180 ถึง 180

    # แปลงเป็น 0-360
    angle = (angle + 360) % 360

    # แบ่ง 8 sector ขนาด 45 องศา แล้ว map ไป cell
    # 0° = ขวา, 90° = ลง, 180° = ซ้าย, 270° = ขึ้น
    sector = int((angle + 22.5) / 45) % 8

    # sector → cell index:
    # sector 0 (ขวา)      → cell 5 (กลางขวา)
    # sector 1 (ขวา-ล่าง) → cell 8 (ล่างขวา)
    # sector 2 (ล่าง)     → cell 7 (ล่างกลาง)
    # sector 3 (ซ้าย-ล่าง)→ cell 6 (ล่างซ้าย)
    # sector 4 (ซ้าย)     → cell 3 (กลางซ้าย)
    # sector 5 (ซ้าย-บน)  → cell 0 (บนซ้าย)
    # sector 6 (บน)       → cell 1 (บนกลาง)
    # sector 7 (ขวา-บน)   → cell 2 (บนขวา)
    _sector_to_cell = [5, 8, 7, 6, 3, 0, 1, 2]
    return _sector_to_cell[sector]


class KeyboardController:
    """จัดการ state ทั้งหมดของ Virtual Keyboard"""

    def __init__(self):
        self.is_active = False
        self._overlay: Optional[KeyboardOverlay] = None

        # Selection state
        self._selected_cell = 4  # ช่องกลาง (ว่าง) เป็น default
        self._char_index = -1  # ยังไม่ได้เลือกตัวอักษร

        # ข้อความที่พิมพ์
        self._typed_text = ""

        # Button state tracking (เพื่อทำ edge detection)
        self._btn_a_prev = False
        self._btn_x_prev = False
        self._btn_y_prev = False
        self._btn_b_prev = False
        self._toggle_btn_prev = False

        # Shift (กดค้างปุ่ม 9 = พิมพ์ใหญ่)
        self.is_shift = False

        # เวลากด A ล่าสุด (ป้องกัน rapid fire)
        self._last_a_time = 0.0

        # เวลาที่ไม่ได้กด A (สำหรับ auto-commit)
        self._last_a_release_time = 0.0
        self._pending_commit = False

    def open(self):
        """เปิด keyboard overlay"""
        self.is_active = True
        self._selected_cell = 4
        self._char_index = -1
        self._pending_commit = False

        if KeyboardOverlay:
            self._overlay = KeyboardOverlay()
            self._overlay.show()
            self._overlay.raise_()

        print("[Keyboard] Opened")

    def close(self):
        """ปิด keyboard overlay"""
        self.is_active = False
        self._pending_commit = False
        if self._overlay:
            self._overlay.close()
            self._overlay = None
        print("[Keyboard] Closed")

    def _commit_current_char(self, ui_virtual):
        """
        'commit' ตัวอักษรที่เลือกอยู่ → เพิ่มลงใน typed_text
        (ยังไม่ส่ง keypress จริง ส่งตอนกด A ครั้งแรก)
        """
        pass  # การพิมพ์จริงเกิดที่ _handle_btn_a แล้ว

    def _handle_analog(self, joystick):
        """อ่าน analog ซ้าย แล้วอัปเดตช่องที่เลือก"""
        try:
            ax = joystick.get_axis(0)
            ay = joystick.get_axis(1)
        except:
            return

        cell = _analog_to_cell(ax, ay)

        if cell is None:
            # อยู่ตรงกลาง deadzone → ช่องกลาง
            new_cell = 4
        else:
            new_cell = cell

        if new_cell != self._selected_cell:
            self._selected_cell = new_cell
            self._char_index = -1  # reset index เมื่อเปลี่ยนช่อง
            self._pending_commit = False
            if self._overlay:
                self._overlay.set_selected_cell(new_cell)
                self._overlay.set_char_index(-1)

    def _handle_btn_a(self, ui_virtual, is_pressed: bool):
        """
        Logic ปุ่ม A:
        - กดครั้งแรก → พิมพ์ตัวแรกของกลุ่ม (ทันที)
        - กดซ้ำเร็วๆ → วนตัวถัดไป (แทนที่ตัวก่อน)
        - ไม่กดนาน _COMMIT_DELAY วิ → commit (ตัวอักษรนั้นถูก type แล้ว reset)
        """
        now = time.time()
        is_just_pressed = is_pressed and not self._btn_a_prev

        if is_just_pressed:
            group = CHAR_GROUPS[self._selected_cell]
            if group is None:
                return  # ช่องกลาง ไม่มี action

            n = len(group)

            if self._char_index < 0:
                # ครั้งแรก → เลือก index 0
                self._char_index = 0
            else:
                # กดซ้ำ → วนไปตัวถัดไป
                self._char_index = (self._char_index + 1) % n

            # อัปเดต UI
            if self._overlay:
                self._overlay.set_char_index(self._char_index)

            # พิมพ์ตัวอักษรทันที
            char = group[self._char_index]

            if self._pending_commit:
                _press_key(ui_virtual, e.KEY_BACKSPACE)
                if self._typed_text:
                    self._typed_text = self._typed_text[:-1]

            # พิมพ์ตัวใหม่ (ใหญ่หรือเล็กตาม shift)
            _type_char(ui_virtual, char, shift=self.is_shift)
            typed_char = char.upper() if self.is_shift else char.lower()
            self._typed_text += typed_char
            self._pending_commit = True

            if self._overlay:
                self._overlay.set_typed_text(self._typed_text)

            self._last_a_time = now
            self._last_a_release_time = 0.0

        elif not is_pressed and self._btn_a_prev:
            # ปล่อยปุ่ม A
            self._last_a_release_time = now

    def _check_auto_commit(self):
        """
        ถ้าปล่อยปุ่ม A ไปนาน _COMMIT_DELAY วิ → commit (reset char_index)
        คือ ถ้าจะพิมพ์ตัวต่อไปในช่องใหม่ก็ทำได้เลย
        """
        if not self._pending_commit:
            return
        if self._last_a_release_time <= 0:
            return

        now = time.time()
        if now - self._last_a_release_time >= _COMMIT_DELAY:
            # commit → reset state ให้พร้อมพิมพ์ตัวต่อไป
            self._char_index = -1
            self._pending_commit = False
            self._last_a_release_time = 0.0
            if self._overlay:
                self._overlay.set_char_index(-1)

    def _handle_btn_x(self, ui_virtual, is_pressed: bool):
        """ปุ่ม X → Backspace"""
        if is_pressed and not self._btn_x_prev:
            # ถ้ากำลัง pending อยู่ ให้ cancel pending ก่อน
            if self._pending_commit:
                self._pending_commit = False
                self._char_index = -1
                if self._overlay:
                    self._overlay.set_char_index(-1)
                # ไม่ต้อง backspace เพิ่ม เพราะตัวอักษรถูก type ไปแล้ว

            _press_key(ui_virtual, e.KEY_BACKSPACE)
            if self._typed_text:
                self._typed_text = self._typed_text[:-1]
                if self._overlay:
                    self._overlay.set_typed_text(self._typed_text)

    def _handle_btn_y(self, ui_virtual, is_pressed: bool):
        """ปุ่ม Y → Space"""
        if is_pressed and not self._btn_y_prev:
            if self._pending_commit:
                self._pending_commit = False
                self._char_index = -1
                if self._overlay:
                    self._overlay.set_char_index(-1)

            _press_key(ui_virtual, e.KEY_SPACE)
            self._typed_text += " "
            if self._overlay:
                self._overlay.set_typed_text(self._typed_text)

    def _handle_btn_b(self, ui_virtual, is_pressed: bool):
        """ปุ่ม B → Enter"""
        if is_pressed and not self._btn_b_prev:
            if self._pending_commit:
                self._pending_commit = False
                self._char_index = -1
                if self._overlay:
                    self._overlay.set_char_index(-1)

            _press_key(ui_virtual, e.KEY_ENTER)
            self._typed_text = ""
            if self._overlay:
                self._overlay.set_typed_text(self._typed_text)

    def _get_button(self, joystick, mapping: dict, key: str) -> bool:
        """อ่านค่าปุ่มจาก mapping"""
        btn_idx = mapping.get("buttons", {}).get(key)
        if btn_idx is None:
            return False
        try:
            if isinstance(btn_idx, int):
                return joystick.get_button(btn_idx)
        except:
            pass
        return False

    def run(self, ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
        """
        Main entry point

        Returns:
            True  → keyboard active, กิน input ทั้งหมด
            False → ไม่ active
        """
        # Trigger mode (จาก sequence engine หรือ radial menu)
        if trigger_key == "toggle_keyboard":
            if self.is_active:
                self.close()
            else:
                self.open()
            return True

        if not joystick:
            return self.is_active

        # ตรวจปุ่ม toggle จาก mapping (edge detection)
        toggle_btn = mod_mapping.get("buttons", {}).get("toggle_keyboard")
        if toggle_btn is not None:
            try:
                if isinstance(toggle_btn, int):
                    pressed = joystick.get_button(toggle_btn)
                elif isinstance(toggle_btn, list):
                    pressed = all(joystick.get_button(b) for b in toggle_btn)
                else:
                    pressed = False

                if pressed and not self._toggle_btn_prev:
                    if self.is_active:
                        self.close()
                    else:
                        self.open()
                self._toggle_btn_prev = pressed
            except:
                pass

        if not self.is_active:
            return False

        # --- Keyboard Active: จัดการ input ทั้งหมด ---

        # Analog → เลือกช่อง
        self._handle_analog(joystick)

        # อ่านปุ่ม
        # อ่านปุ่มจาก mapping
        buttons = mod_mapping.get("buttons", {})
        idx_a = buttons.get("select", 0)
        idx_b = buttons.get("enter", 1)
        idx_x = buttons.get("backspace", 3)
        idx_y = buttons.get("space", 4)
        idx_shift = buttons.get("shift", 9)

        try:
            btn_a = joystick.get_button(idx_a)
            btn_b = joystick.get_button(idx_b)
            btn_x = joystick.get_button(idx_x)
            btn_y = joystick.get_button(idx_y)
            self.is_shift = joystick.get_button(idx_shift)  # กดค้าง = shift
        except:
            btn_a = btn_b = btn_x = btn_y = False
            self.is_shift = False

        self._handle_btn_a(ui_virtual, btn_a)
        self._handle_btn_x(ui_virtual, btn_x)
        self._handle_btn_y(ui_virtual, btn_y)
        self._handle_btn_b(ui_virtual, btn_b)

        # Auto-commit check
        self._check_auto_commit()

        # อัปเดต state เก่า
        self._btn_a_prev = btn_a
        self._btn_x_prev = btn_x
        self._btn_y_prev = btn_y
        self._btn_b_prev = btn_b

        # update overlay
        if self._overlay:
            self._overlay.set_shift(self.is_shift)
            self._overlay.update()

        return True  # กิน input ทั้งหมด


# Global instance
_controller = KeyboardController()


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    return _controller.run(ui_virtual, joystick, app_config, mod_mapping, trigger_key)
