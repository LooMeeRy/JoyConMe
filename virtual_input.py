import sys
import time


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
                caps = {
                    e.EV_REL: (e.REL_X, e.REL_Y, e.REL_WHEEL),
                    e.EV_KEY: [
                        e.BTN_LEFT,
                        e.BTN_RIGHT,
                        e.KEY_BACKSPACE,
                        e.KEY_ENTER,
                        e.KEY_SPACE,
                        e.KEY_LEFTSHIFT,
                    ]
                    + list(range(2, 58)),
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

    # --- ส่วนที่เพิ่มใหม่สำหรับ Keyboard ---
    def tap_special(self, evdev_code, pynput_key_str):
        """สำหรับปุ่มพิเศษ เช่น backspace, enter, space"""
        if self.backend == "evdev":
            self.uinput.write(self.e.EV_KEY, evdev_code, 1)
            self.uinput.syn()
            time.sleep(0.02)
            self.uinput.write(self.e.EV_KEY, evdev_code, 0)
            self.uinput.syn()
        else:
            k = self.special_keys.get(pynput_key_str)
            if k:
                self.keyboard.press(k)
                self.keyboard.release(k)

    def type_char(self, evdev_code, char_str, shift=False):
        """สำหรับพิมพ์ตัวอักษรปกติ"""
        if self.backend == "evdev":
            if shift:
                self.uinput.write(self.e.EV_KEY, self.e.KEY_LEFTSHIFT, 1)
                self.uinput.syn()
            self.uinput.write(self.e.EV_KEY, evdev_code, 1)
            self.uinput.syn()
            time.sleep(0.02)
            self.uinput.write(self.e.EV_KEY, evdev_code, 0)
            self.uinput.syn()
            if shift:
                self.uinput.write(self.e.EV_KEY, self.e.KEY_LEFTSHIFT, 0)
                self.uinput.syn()
        else:
            # pynput จะพิมพ์อักขระพิเศษและ Shift ออกมาตาม string ได้เลยอัตโนมัติ
            self.keyboard.type(char_str)

    def close(self):
        if self.backend == "evdev":
            self.uinput.close()
