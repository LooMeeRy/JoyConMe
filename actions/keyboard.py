import importlib
import subprocess
import time
from typing import Optional

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    from ui.keyboard_ui import CHAR_GROUPS, NUM_GROUPS, SYM_GROUPS, EMOJI_GROUPS, KeyboardOverlay
except ImportError:
    KeyboardOverlay = None
    CHAR_GROUPS = ["ABC", "DEF", "GHI", "JKL", None, "MNO", "PQR", "STUV", "WXYZ"]
    NUM_GROUPS = ["123", "456", "789", "0-=", None, "[]\\", ";'", ",.", "/`"]
    SYM_GROUPS = ["!@#", "$%^", "&*(", ")_+", None, "{}|", ':"', "<>", "?~"]
    EMOJI_GROUPS = [
        "😊😂😍🥰😘😎",
        "👍👎👌✌🤞🖕",
        "❤️💔💕💖💗💘",
        "🔥💯⭐🌟✨💫",
        None,
        "🐶🐱🐼🐸🦊🐰",
        "🍕🍔🌮🍩🍦🍰",
        "⚽🎮🎵🎸🎯🎨",
        "🚗✈️🌍🌈🌊🔥",
    ]



ACTION_INFO = {
    "id": "keyboard",
    "name": "คีย์บอร์ดเสมือน",
    "priority": 2,
    "is_blocking": True,
    "actions": [
        {"key": "toggle_keyboard", "type": "button", "desc": "เปิด/ปิด คีย์บอร์ด"},
        {"key": "num_shift", "type": "button", "desc": "โหมดตัวเลข"},
        {"key": "select", "type": "button", "desc": "เลือก"},
        {"key": "enter", "type": "button", "desc": "ยืนยัน"},
        {"key": "backspace", "type": "button", "desc": "ลบ"},
        {"key": "space", "type": "button", "desc": "เว้นวรรค"},
        {"key": "shift", "type": "button", "desc": "shift"},
        {"key": "emoji_toggle", "type": "button", "desc": "เปลี่ยนเป็นโหมดอิโมจิ"},
    ],
}

_DEADZONE = 0.45
_CYCLE_DELAY = 0.25
_COMMIT_DELAY = 1.2


def _type_char(ui_virtual, char: str, is_upper: bool = False):
    ui_virtual.type_char(char, shift=is_upper)


def _analog_to_cell(ax: float, ay: float) -> Optional[int]:
    if abs(ax) < _DEADZONE and abs(ay) < _DEADZONE:
        return None
    import math

    angle = math.degrees(math.atan2(ay, ax))
    angle = (angle + 360) % 360
    sector = int((angle + 22.5) / 45) % 8
    _sector_to_cell = [5, 8, 7, 6, 3, 0, 1, 2]
    return _sector_to_cell[sector]


class KeyboardController:
    def __init__(self):
        self.is_active = False
        self._overlay: Optional[KeyboardOverlay] = None
        self._selected_cell = 4
        self._char_index = -1
        self._typed_text = ""
        self._btn_a_prev = False
        self._btn_x_prev = False
        self._btn_y_prev = False
        self._btn_b_prev = False
        self._toggle_btn_prev = False
        self._emoji_toggle_btn_prev = False
        self.is_shift = False
        self.is_num_mode = False
        self.is_emoji_mode = False
        self._last_a_time = 0.0
        self._last_a_release_time = 0.0
        self._pending_commit = False

    def open(self):
        self.is_active = True
        self._selected_cell = 4
        self._char_index = -1
        self._pending_commit = False
        self.is_emoji_mode = False
        if KeyboardOverlay:
            self._overlay = KeyboardOverlay()
            self._overlay.show()

    def close(self):
        self.is_active = False
        self._pending_commit = False
        if self._overlay:
            self._overlay.close()
            self._overlay = None

    def _handle_analog(self, joystick):
        try:
            ax = joystick.get_axis(0)
            ay = joystick.get_axis(1)
        except:
            return

        cell = _analog_to_cell(ax, ay)
        new_cell = 4 if cell is None else cell

        if new_cell != self._selected_cell:
            self._selected_cell = new_cell
            self._char_index = -1
            self._pending_commit = False
            if self._overlay:
                self._overlay.set_selected_cell(new_cell)
                self._overlay.set_char_index(-1)

    def _paste_emoji(self, ui_virtual, emoji: str):
        """คัดลอก emoji เข้าคลิปบอร์ดแล้ว paste ด้วย Ctrl+V"""
        try:
            if pyperclip:
                pyperclip.copy(emoji)
            else:
                subprocess.run(["wl-copy", emoji], check=False, timeout=2)
        except:
            return
        time.sleep(0.05)
        ui_virtual.press_special('ctrl', True)
        ui_virtual.press_special('v', True)
        time.sleep(0.02)
        ui_virtual.press_special('v', False)
        ui_virtual.press_special('ctrl', False)

    def _handle_btn_a(self, ui_virtual, is_pressed: bool):
        now = time.time()
        is_just_pressed = is_pressed and not self._btn_a_prev

        if is_just_pressed:
            if self.is_emoji_mode:
                group = EMOJI_GROUPS[self._selected_cell]
            elif self.is_num_mode and self.is_shift:
                group = SYM_GROUPS[self._selected_cell]
            elif self.is_num_mode:
                group = NUM_GROUPS[self._selected_cell]
            else:
                group = CHAR_GROUPS[self._selected_cell]

            if group is None:
                # ศูนย์กลาง = ออกจากโหมดอิโมจิ
                if self.is_emoji_mode:
                    self.is_emoji_mode = False
                    self._char_index = -1
                    self._pending_commit = False
                    if self._overlay:
                        self._overlay.set_selected_cell(self._selected_cell)
                        self._overlay.set_mode(self.is_shift, self.is_num_mode, self.is_emoji_mode)
                return

            n = len(group)
            if self._char_index < 0:
                self._char_index = 0
            else:
                self._char_index = (self._char_index + 1) % n

            if self._overlay:
                self._overlay.set_char_index(self._char_index)

            char = group[self._char_index]

            if self._pending_commit:
                ui_virtual.tap_special('backspace')
                if self._typed_text:
                    self._typed_text = self._typed_text[:-1]

            if self.is_emoji_mode:
                # อิโมจิ → คลิปบอร์ด + paste
                emoji_char = char
                self._paste_emoji(ui_virtual, emoji_char)
                self._typed_text += emoji_char
            else:
                _type_char(ui_virtual, char, is_upper=self.is_shift)
                if not self.is_num_mode:
                    typed_char = char.upper() if self.is_shift else char.lower()
                else:
                    typed_char = char
                self._typed_text += typed_char

            self._pending_commit = True

            if self._overlay:
                self._overlay.set_typed_text(self._typed_text)

            self._last_a_time = now
            self._last_a_release_time = 0.0

        elif not is_pressed and self._btn_a_prev:
            self._last_a_release_time = now

    def _check_auto_commit(self):
        if not self._pending_commit:
            return
        if self._last_a_release_time <= 0:
            return
        now = time.time()
        if now - self._last_a_release_time >= _COMMIT_DELAY:
            self._char_index = -1
            self._pending_commit = False
            self._last_a_release_time = 0.0
            if self._overlay:
                self._overlay.set_char_index(-1)

    def _handle_btn_x(self, ui_virtual, is_pressed: bool):
        if is_pressed and not self._btn_x_prev:
            if self._pending_commit:
                self._pending_commit = False
                self._char_index = -1
                if self._overlay:
                    self._overlay.set_char_index(-1)
            ui_virtual.tap_special('backspace')
            if self._typed_text:
                self._typed_text = self._typed_text[:-1]
                if self._overlay:
                    self._overlay.set_typed_text(self._typed_text)

    def _handle_btn_y(self, ui_virtual, is_pressed: bool):
        if is_pressed and not self._btn_y_prev:
            if self._pending_commit:
                self._pending_commit = False
                self._char_index = -1
                if self._overlay:
                    self._overlay.set_char_index(-1)
            ui_virtual.tap_special('space')
            self._typed_text += " "
            if self._overlay:
                self._overlay.set_typed_text(self._typed_text)

    def _handle_btn_b(self, ui_virtual, is_pressed: bool):
        if is_pressed and not self._btn_b_prev:
            # 🎯 ถ้าอยู่ในโหมดอิโมจิและเลือกช่องกลาง → ออกจากโหมด
            if self.is_emoji_mode and self._selected_cell == 4:
                self.is_emoji_mode = False
                self._char_index = -1
                self._pending_commit = False
                if self._overlay:
                    self._overlay.set_selected_cell(self._selected_cell)
                    self._overlay.set_mode(self.is_shift, self.is_num_mode, self.is_emoji_mode)
                return

            if self._pending_commit:
                self._pending_commit = False
                self._char_index = -1
                if self._overlay:
                    self._overlay.set_char_index(-1)
            ui_virtual.tap_special('enter')
            self._typed_text = ""
            if self._overlay:
                self._overlay.set_typed_text(self._typed_text)

    def run(self, ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
        if trigger_key == "toggle_keyboard":
            if self.is_active:
                self.close()
            else:
                self.open()
            return True

        if not joystick:
            return self.is_active

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

        # 🎯 ปุ่ม toggle โหมดอิโมจิ
        emoji_btn = mod_mapping.get("buttons", {}).get("emoji_toggle")
        if emoji_btn is not None and self.is_active:
            try:
                if isinstance(emoji_btn, int):
                    pressed = joystick.get_button(emoji_btn)
                elif isinstance(emoji_btn, list):
                    pressed = all(joystick.get_button(b) for b in emoji_btn)
                else:
                    pressed = False

                if pressed and not self._emoji_toggle_btn_prev:
                    self.is_emoji_mode = not self.is_emoji_mode
                    self._char_index = -1
                    self._pending_commit = False
                    if self._overlay:
                        self._overlay.set_selected_cell(self._selected_cell)
                        self._overlay.set_mode(self.is_shift, self.is_num_mode, self.is_emoji_mode)
                self._emoji_toggle_btn_prev = pressed
            except:
                pass

        if not self.is_active:
            return False

        self._handle_analog(joystick)

        buttons = mod_mapping.get("buttons", {})
        idx_a = buttons.get("select", 0)
        idx_b = buttons.get("enter", 1)
        idx_x = buttons.get("backspace", 3)
        idx_y = buttons.get("space", 4)
        idx_shift = buttons.get("shift", 9)
        idx_num_shift = buttons.get("num_shift", 4)

        try:
            btn_a = joystick.get_button(idx_a)
            btn_b = joystick.get_button(idx_b)
            btn_x = joystick.get_button(idx_x)
            btn_y = joystick.get_button(idx_y)
            self.is_shift = joystick.get_button(idx_shift)
            self.is_num_mode = (
                joystick.get_button(idx_num_shift)
                if idx_num_shift is not None
                else False
            )
        except:
            btn_a = btn_b = btn_x = btn_y = False
            self.is_shift = self.is_num_mode = False

        self._handle_btn_a(ui_virtual, btn_a)
        self._handle_btn_x(ui_virtual, btn_x)
        self._handle_btn_y(ui_virtual, btn_y)
        self._handle_btn_b(ui_virtual, btn_b)

        self._check_auto_commit()

        self._btn_a_prev = btn_a
        self._btn_x_prev = btn_x
        self._btn_y_prev = btn_y
        self._btn_b_prev = btn_b

        if self._overlay:
            self._overlay.set_mode(self.is_shift, self.is_num_mode, self.is_emoji_mode)

        return True


_controller = KeyboardController()


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    return _controller.run(ui_virtual, joystick, app_config, mod_mapping, trigger_key)
