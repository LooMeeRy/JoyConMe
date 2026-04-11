import os
import signal
import sys
from pathlib import Path

# อนุญาตให้ Pygame อ่านจอยแม้โปรแกรมจะอยู่เบื้องหลัง
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# Add project root to path (สำหรับกรณีรันจากที่อื่น)
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from engine import JoyConEngine


class JoyConApp:
    """Wrapper class สำหรับจัดการ Application Lifecycle ด้วย QTimer (Qt-Native)"""

    def __init__(self):
        # สร้าง QApplication ก่อน
        self.app = QApplication(sys.argv)
        self.engine = JoyConEngine()

        # 1. Main Engine Timer: ทำหน้าที่รัน Tick ของเกมแพด
        self.engine_timer = QTimer()
        self.engine_timer.timeout.connect(self._run_tick)

        # 2. Signal Catcher Timer: ทริคสำหรับให้ Python ตรวจจับ Ctrl+C ได้ขณะรัน Qt Event Loop
        self.signal_timer = QTimer()
        self.signal_timer.timeout.connect(lambda: None)

    def _signal_handler(self, signum, frame):
        """จัดการการกด Ctrl+C เพื่อปิดโปรแกรมอย่างปลอดภัย"""
        print("\n⚠️ ได้รับสัญญาณหยุด...")
        self.cleanup()

    def _setup_signal_handlers(self):
        """ตั้งค่า Signal Handlers"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._signal_handler)

    def run(self):
        """เริ่มการทำงานของแอปพลิเคชัน"""
        self._setup_signal_handlers()

        try:
            print("🚀 ระบบ JoyConMe พร้อมทำงาน (Native Qt Loop)...")
            print("   - กด Ctrl+C เพื่อหยุด")
            print("   - หรือใช้สูตรลับปิดโปรแกรม (ถ้าตั้งไว้)")

            # คำนวณ Tick Rate เป็น Milliseconds (วินาที * 1000)
            interval_ms = int(self.engine.get_sleep_time() * 1000)

            # เริ่มทำงาน Timer ทั้งสองตัว
            self.engine_timer.start(interval_ms)
            self.signal_timer.start(500)  # ให้ Python ตื่นมาเช็ค Signal ทุกๆ 0.5 วิ

            # เข้าสู่ Native Qt Event Loop (บล็อกการทำงานไว้ที่นี่จนกว่าจะปิดแอป)
            exit_code = self.app.exec()
            sys.exit(exit_code)

        except Exception as e:
            print(f"\n❌ Fatal Error: {e}")
            import traceback

            traceback.print_exc()
            self.cleanup()

    def _run_tick(self):
        """ฟังก์ชันที่ถูกเรียกซ้ำๆ ตามค่า Interval ของ QTimer"""
        try:
            self.engine.run_tick()
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
            except Exception as e:
                print(f"⚠️ Error during cleanup: {e}")

        # สั่งปิดหน้าต่าง UI และ Event Loop
        self.app.quit()
        print("👋 ปิดโปรแกรมเรียบร้อย")
        sys.exit(0)


def main():
    """Entry point"""
    # ตรวจสอบ Python version
    if sys.version_info < (3, 8):
        print("❌ ต้องการ Python 3.8+")
        sys.exit(1)

    # ตรวจสอบ Linux (evdev ใช้ได้เฉพาะ Linux)
    if sys.platform != "linux":
        print("⚠️ Warning: evdev อาจทำงานไม่เต็มที่บน OS นี้")

    app = JoyConApp()
    app.run()


if __name__ == "__main__":
    main()
