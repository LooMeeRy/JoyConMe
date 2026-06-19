import sys
import time

_E_MAP = {
    "a": ("KEY_A", False), "b": ("KEY_B", False), "c": ("KEY_C", False),
    "d": ("KEY_D", False), "e": ("KEY_E", False), "f": ("KEY_F", False),
    "g": ("KEY_G", False), "h": ("KEY_H", False), "i": ("KEY_I", False),
    "j": ("KEY_J", False), "k": ("KEY_K", False), "l": ("KEY_L", False),
    "m": ("KEY_M", False), "n": ("KEY_N", False), "o": ("KEY_O", False),
    "p": ("KEY_P", False), "q": ("KEY_Q", False), "r": ("KEY_R", False),
    "s": ("KEY_S", False), "t": ("KEY_T", False), "u": ("KEY_U", False),
    "v": ("KEY_V", False), "w": ("KEY_W", False), "x": ("KEY_X", False),
    "y": ("KEY_Y", False), "z": ("KEY_Z", False),
    "1": ("KEY_1", False), "!": ("KEY_1", True),
    "2": ("KEY_2", False), "@": ("KEY_2", True),
    "3": ("KEY_3", False), "#": ("KEY_3", True),
    "4": ("KEY_4", False), "$": ("KEY_4", True),
    "5": ("KEY_5", False), "%": ("KEY_5", True),
    "6": ("KEY_6", False), "^": ("KEY_6", True),
    "7": ("KEY_7", False), "&": ("KEY_7", True),
    "8": ("KEY_8", False), "*": ("KEY_8", True),
    "9": ("KEY_9", False), "(": ("KEY_9", True),
    "0": ("KEY_0", False), ")": ("KEY_0", True),
    "-": ("KEY_MINUS", False), "_": ("KEY_MINUS", True),
    "=": ("KEY_EQUAL", False), "+": ("KEY_EQUAL", True),
    "[": ("KEY_LEFTBRACE", False), "{": ("KEY_LEFTBRACE", True),
    "]": ("KEY_RIGHTBRACE", False), "}": ("KEY_RIGHTBRACE", True),
    "\\": ("KEY_BACKSLASH", False), "|": ("KEY_BACKSLASH", True),
    ";": ("KEY_SEMICOLON", False), ":": ("KEY_SEMICOLON", True),
    "'": ("KEY_APOSTROPHE", False), '"': ("KEY_APOSTROPHE", True),
    ",": ("KEY_COMMA", False), "<": ("KEY_COMMA", True),
    ".": ("KEY_DOT", False), ">": ("KEY_DOT", True),
    "/": ("KEY_SLASH", False), "?": ("KEY_SLASH", True),
    "`": ("KEY_GRAVE", False), "~": ("KEY_GRAVE", True),
}

class VirtualInput:
    """
    Hybrid Abstraction Layer สำหรับเมาส์และคีย์บอร์ด
    Linux -> evdev (UInput)
    Windows/Mac -> pynput
    """

    def __init__(self, device_name="JoyConMe"):
        self.is_linux = sys.platform == "linux"
        self.backend = "pynput"

        if self.is_linux:
            try:
                from evdev import UInput
                from evdev import ecodes as e

                self.e = e
                # Register mouse axes and all keys simply by checking constants
                caps = {
                    e.EV_REL: (e.REL_X, e.REL_Y, e.REL_WHEEL),
                    e.EV_KEY: [
                        e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE,
                        e.KEY_BACKSPACE, e.KEY_ENTER, e.KEY_SPACE, e.KEY_LEFTSHIFT, e.KEY_LEFTCTRL, e.KEY_V
                    ] + list(range(2, 58)),
                }
                self.uinput = UInput(caps, name=device_name)
                self.backend = "evdev"
                print("✅ Virtual Input: evdev (Linux Kernel Mode)")
            except Exception as ex:
                print(f"⚠️ evdev ไม่พร้อมทำงาน: {ex}\nสลับไปใช้ pynput...")
                self.is_linux = False

        if not self.is_linux:
            from pynput.keyboard import Controller as KeyboardController
            from pynput.keyboard import Key
            from pynput.mouse import Button
            from pynput.mouse import Controller as MouseController

            self.mouse = MouseController()
            self.keyboard = KeyboardController()
            self.mouse_btns = {"left": Button.left, "right": Button.right}

            self.special_keys = {
                "backspace": Key.backspace,
                "enter": Key.enter,
                "space": Key.space,
                "shift": Key.shift,
                "ctrl": Key.ctrl_l,
                "v": "v",
            }
            self.backend = "pynput"
            print("✅ Virtual Input: pynput (Cross-Platform Mode)")

    def mouse_move(self, dx, dy):
        if self.backend == "evdev":
            if dx != 0:
                self.uinput.write(self.e.EV_REL, self.e.REL_X, dx)
            if dy != 0:
                self.uinput.write(self.e.EV_REL, self.e.REL_Y, dy)
            self.uinput.syn()
        else:
            self.mouse.move(dx, dy)

    def mouse_scroll(self, amount):
        if self.backend == "evdev":
            self.uinput.write(self.e.EV_REL, self.e.REL_WHEEL, amount)
            self.uinput.syn()
        else:
            self.mouse.scroll(0, -amount if amount < 0 else amount)

    def mouse_click(self, button_name, is_press):
        if self.backend == "evdev":
            btn_code = self.e.BTN_LEFT if button_name == "left" else self.e.BTN_RIGHT
            self.uinput.write(self.e.EV_KEY, btn_code, 1 if is_press else 0)
            self.uinput.syn()
        else:
            btn = self.mouse_btns.get(button_name)
            if is_press:
                self.mouse.press(btn)
            else:
                self.mouse.release(btn)

    def tap_special(self, key_str):
        """สำหรับปุ่มพิเศษ เช่น backspace, enter, space"""
        self.press_special(key_str, True)
        time.sleep(0.02)
        self.press_special(key_str, False)

    def press_special(self, key_str, is_press):
        """กดปุ่มค้าง หรือกดพร้อมกัน (Combo)"""
        aliases = {
            "ctrl": "leftctrl", "lctrl": "leftctrl", "rctrl": "rightctrl",
            "shift": "leftshift", "lshift": "leftshift", "rshift": "rightshift",
            "alt": "leftalt"
        }
        evdev_key_str = aliases.get(key_str.lower(), key_str)
        
        if self.backend == "evdev":
            key_name = f"KEY_{evdev_key_str.upper()}"
            code = getattr(self.e, key_name, None)
            if code is not None:
                self.uinput.write(self.e.EV_KEY, code, 1 if is_press else 0)
                self.uinput.syn()
        else:
            # pynput mode
            k = self.special_keys.get(key_str.lower())
            if not k and hasattr(self.keyboard._Key, key_str.lower()): # Try to find in pynput.keyboard.Key
                k = getattr(self.keyboard._Key, key_str.lower(), None)
            if not k and len(key_str) == 1:
                k = key_str
            
            if k:
                if is_press:
                    self.keyboard.press(k)
                else:
                    self.keyboard.release(k)

    def type_char(self, char_str, shift=False):
        """สำหรับพิมพ์ตัวอักษรปกติ"""
        if self.backend == "evdev":
            mapping = _E_MAP.get(char_str.lower())
            if not mapping:
                return
            key_name, req_shift = mapping
            code = getattr(self.e, key_name, None)
            if not code:
                return
            do_shift = shift or req_shift
            if do_shift:
                self.uinput.write(self.e.EV_KEY, self.e.KEY_LEFTSHIFT, 1)
                self.uinput.syn()
            self.uinput.write(self.e.EV_KEY, code, 1)
            self.uinput.syn()
            time.sleep(0.02)
            self.uinput.write(self.e.EV_KEY, code, 0)
            self.uinput.syn()
            if do_shift:
                self.uinput.write(self.e.EV_KEY, self.e.KEY_LEFTSHIFT, 0)
                self.uinput.syn()
        else:
            self.keyboard.type(char_str)

    def close(self):
        if self.backend == "evdev":
            self.uinput.close()
