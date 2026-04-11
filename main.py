import os
import signal
import sys
import time
from pathlib import Path

# อนุญาตให้ Pygame อ่านจอยแม้โปรแกรมจะอยู่เบื้องหลัง
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from engine import JoyConEngine


class JoyConApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.engine = JoyConEngine()

        # 1. Main Engine Timer
        self.engine_timer = QTimer()
        self.engine_timer.timeout.connect(self._run_tick)

        # 2. Signal Catcher Timer
        self.signal_timer = QTimer()
        self.signal_timer.timeout.connect(lambda: None)

    def _signal_handler(self, signum, frame):
        print("\n⚠️ ได้รับสัญญาณหยุด (Signal Interrupt)...")
        self.cleanup()

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._signal_handler)

    def run(self):
        """เริ่มการทำงานของแอปพลิเคชัน พร้อมแสดง Boot Logs"""
        self._setup_signal_handlers()

        # 🚀 ส่วนแสดง Boot Logs (สวยงาม)
        try:
            print("\n" + "⚡" * 25)
            print("   JOYCON-ME SYSTEM STARTING...")
            print("⚡" * 25)

            print(f"🖥️  UI System   : Qt for Python (Ready)")

            # ตรวจเช็คชื่อจอย
            joy_name = (
                self.engine._joystick.get_name()
                if self.engine._joystick
                else "Not Found"
            )
            print(f"🎮 Controller  : {joy_name}")

            # คำนวณ Tick Rate
            interval_ms = int(self.engine.get_sleep_time() * 1000)
            print(
                f"⏱️  Performance : {1000 / interval_ms:.0f} Hz (Tick: {interval_ms}ms)"
            )

            # แสดงรายชื่อ Action ที่โหลดมา (Engine จะ print ตารางนี้ตอนโหลด)
            # เราเรียก _load_actions ใหม่ที่นี่เพื่อโชว์ log สวยๆ (ถ้า Engine ยังไม่ได้ทำ)
            # self.engine._load_actions()

            print("\n💡 System is running in background.")
            print("   - Press Ctrl+C to stop.")
            print("   - Or use secret sequence to Exit.")
            print("-" * 55)

            # เริ่มทำงาน Timer
            self.engine_timer.start(interval_ms)
            self.signal_timer.start(500)

            # เข้าสู่ Qt Event Loop
            exit_code = self.app.exec()
            sys.exit(exit_code)

        except Exception as e:
            # ✨ บรรทัดที่หายไปและทำให้เกิด SyntaxError คือกลุ่มนี้ครับ!
            print(f"\n❌ Fatal Error during startup: {e}")
            self.cleanup()

    def _run_tick(self):
        """รันรอบการทำงานของ Engine และเช็คสัญญาณพิเศษ"""
        try:
            result = self.engine.run_tick()

            # ตรวจสอบสัญญาณปิดโปรแกรม
            if result == "EXIT":
                print("\n🛑 [Main] Received EXIT signal. Closing...")
                self.cleanup()
            elif result == "SAVE_CONFIG":
                self.engine.save_app_config()

        except Exception as e:
            print(f"⚠️ Error in engine tick loop: {e}")

    def cleanup(self):
        """คืนค่าทรัพยากรทั้งหมดก่อนปิดแอป"""
        print("\nกำลังปิดระบบ...")
        self.engine_timer.stop()
        self.signal_timer.stop()

        if self.engine:
            try:
                self.engine.cleanup()
            except:
                pass

        self.app.quit()
        print("👋 ปิดโปรแกรมเรียบร้อย")
        sys.exit(0)


def main():
    app = JoyConApp()
    app.run()


if __name__ == "__main__":
    main()
