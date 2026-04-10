import time
from typing import Optional

from evdev import ecodes as e

try:
    from ui.keyboard_ui import CHAR_GROUPS, NUM_GROUPS, SYM_GROUPS, KeyboardOverlay
except ImportError:
    KeyboardOverlay = None
    CHAR_GROUPS = ["ABC", "DEF", "GHI", "JKL", None, "MNO", "PQR", "STUV", "WXYZ"]
    NUM_GROUPS = ["123", "456", "789", "0-=", None, "[]\\", ";'", ",.", "/`"]
    SYM_GROUPS = ["!@#", "$%^", "&*(", ")_+", None, "{}|", ':"', "<>", "?~"]

# Map ทุกตัวอักษรไปที่ evdev keycode พร้อมบอกว่าต้องกด Shift ด้วยไหม
_CHAR_MAP = {
    "a": (e.KEY_A, False),
    "b": (e.KEY_B, False),
    "c": (e.KEY_C, False),
    "d": (e.KEY_D, False),
    "e": (e.KEY_E, False),
    "f": (e.KEY_F, False),
    "g": (e.KEY_G, False),
    "h": (e.KEY_H, False),
    "i": (e.KEY_I, False),
    "j": (e.KEY_J, False),
    "k": (e.KEY_K, False),
    "l": (e.KEY_L, False),
    "m": (e.KEY_M, False),
    "n": (e.KEY_N, False),
    "o": (e.KEY_O, False),
    "p": (e.KEY_P, False),
    "q": (e.KEY_Q, False),
    "r": (e.KEY_R, False),
    "s": (e.KEY_S, False),
    "t": (e.KEY_T, False),
    "u": (e.KEY_U, False),
    "v": (e.KEY_V, False),
    "w": (e.KEY_W, False),
    "x": (e.KEY_X, False),
    "y": (e.KEY_Y, False),
    "z": (e.KEY_Z, False),
    "1": (e.KEY_1, False),
    "!": (e.KEY_1, True),
    "2": (e.KEY_2, False),
    "@": (e.KEY_2, True),
    "3": (e.KEY_3, False),
    "#": (e.KEY_3, True),
    "4": (e.KEY_4, False),
    "$": (e.KEY_4, True),
    "5": (e.KEY_5, False),
    "%": (e.KEY_5, True),
    "6": (e.KEY_6, False),
    "^": (e.KEY_6, True),
    "7": (e.KEY_7, False),
    "&": (e.KEY_7, True),
    "8": (e.KEY_8, False),
    "*": (e.KEY_8, True),
    "9": (e.KEY_9, False),
    "(": (e.KEY_9, True),
    "0": (e.KEY_0, False),
    ")": (e.KEY_0, True),
    "-": (e.KEY_MINUS, False),
    "_": (e.KEY_MINUS, True),
    "=": (e.KEY_EQUAL, False),
    "+": (e.KEY_EQUAL, True),
    "[": (e.KEY_LEFTBRACE, False),
    "{": (e.KEY_LEFTBRACE, True),
    "]": (e.KEY_RIGHTBRACE, False),
    "}": (e.KEY_RIGHTBRACE, True),
    "\\": (e.KEY_BACKSLASH, False),
    "|": (e.KEY_BACKSLASH, True),
    ";": (e.KEY_SEMICOLON, False),
    ":": (e.KEY_SEMICOLON, True),
    "'": (e.KEY_APOSTROPHE, False),
    '"': (e.KEY_APOSTROPHE, True),
    ",": (e.KEY_COMMA, False),
    "<": (e.KEY_COMMA, True),
    ".": (e.KEY_DOT, False),
    ">": (e.KEY_DOT, True),
    "/": (e.KEY_SLASH, False),
    "?": (e.KEY_SLASH, True),
    "`": (e.KEY_GRAVE, False),
    "~": (e.KEY_GRAVE, True),
}

ACTION_INFO = {
    "id": "keyboard",
    "name": "คีย์บอร์ดเสมือน",
    "actions": [
        {"key": "toggle_keyboard", "type": "button", "desc": "เปิด/ปิด คีย์บอร์ด"},
        {"key": "num_shift", "type": "button", "desc": "กดค้างเพื่อใช้โหมดตัวเลข (เช่น L1)"},
    ],
}

_DEADZONE = 0.45
_CYCLE_DELAY = 0.25
_COMMIT_DELAY = 1.2


def _press_key(ui_virtual, keycode: int):
    try:
        ui_virtual.write(e.EV_KEY, keycode, 1)
        ui_virtual.syn()
        time.sleep(0.02)
        ui_virtual.write(e.EV_KEY, keycode, 0)
        ui_virtual.syn()
    except Exception as ex:
        pass


def _type_char(ui_virtual, char: str, is_upper: bool = False):
    if char.isalpha() and char.isascii():
        kc = _CHAR_MAP.get(char.lower(), (None, False))[0]
        shift = is_upper
    elif char in _CHAR_MAP:
        kc, shift = _CHAR_MAP[char]
    else:
        return

    if not kc:
        return

    if shift:
        ui_virtual.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
        ui_virtual.syn()

    _press_key(ui_virtual, kc)

    if shift:
        ui_virtual.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
        ui_virtual.syn()


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
        self.is_shift = False
        self.is_num_mode = False
        self._last_a_time = 0.0
        self._last_a_release_time = 0.0
        self._pending_commit = False

    def open(self):
        self.is_active = True
        self._selected_cell = 4
        self._char_index = -1
        self._pending_commit = False
        if KeyboardOverlay:
            self._overlay = KeyboardOverlay()
            self._overlay.show()
            self._overlay.raise_()

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

    def _handle_btn_a(self, ui_virtual, is_pressed: bool):
        now = time.time()
        is_just_pressed = is_pressed and not self._btn_a_prev

        if is_just_pressed:
            if self.is_num_mode and self.is_shift:
                group = SYM_GROUPS[self._selected_cell]
            elif self.is_num_mode:
                group = NUM_GROUPS[self._selected_cell]
            else:
                group = CHAR_GROUPS[self._selected_cell]

            if group is None:
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
                _press_key(ui_virtual, e.KEY_BACKSPACE)
                if self._typed_text:
                    self._typed_text = self._typed_text[:-1]

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
            _press_key(ui_virtual, e.KEY_BACKSPACE)
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
            _press_key(ui_virtual, e.KEY_SPACE)
            self._typed_text += " "
            if self._overlay:
                self._overlay.set_typed_text(self._typed_text)

    def _handle_btn_b(self, ui_virtual, is_pressed: bool):
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

        if not self.is_active:
            return False

        self._handle_analog(joystick)

        buttons = mod_mapping.get("buttons", {})
        idx_a = buttons.get("select", 0)
        idx_b = buttons.get("enter", 1)
        idx_x = buttons.get("backspace", 3)
        idx_y = buttons.get("space", 4)
        idx_shift = buttons.get("shift", 9)

        # ตั้งค่าให้ปุ่ม L1 (ค่าเริ่มต้นปกติคือปุ่ม 4 หรือ 6) เป็นตัวสลับโหมดตัวเลข
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
            self.is_shift = False
            self.is_num_mode = False

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
            self._overlay.set_mode(self.is_shift, self.is_num_mode)

        return True


_controller = KeyboardController()


def run(ui_virtual, joystick, app_config, mod_mapping, trigger_key=None):
    return _controller.run(ui_virtual, joystick, app_config, mod_mapping, trigger_key)
