import signal
import sys
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication

# Add project root to path (สำหรับกรณีรันจากที่อื่น)
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from engine import JoyConEngine


class JoyConApp:
    """Wrapper class สำหรับจัดการ Application Lifecycle"""

    def __init__(self):
        self.app: QApplication = None
        self.engine: JoyConEngine = None
        self._running = False

    def _signal_handler(self, signum, frame):
        """จัดการ Ctrl+C"""
        print("\n⚠️ ได้รับสัญญาณหยุด...")
        self._running = False

    def _setup_signal_handlers(self):
        """ตั้งค่า Signal Handlers"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # สำหรับ Windows
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._signal_handler)

    def run(self):
        """Main loop"""
        # สร้าง QApplication ก่อน
        self.app = QApplication(sys.argv)

        # ตั้งค่า Signal
        self._setup_signal_handlers()

        try:
            # สร้าง Engine
            self.engine = JoyConEngine()

            print("🚀 ระบบ JoyConMe พร้อมทำงาน...")
            print("   - กด Ctrl+C เพื่อหยุด")
            print("   - หรือใช้สูตรลับปิดโปรแกรม (ถ้าตั้งไว้)")

            self._running = True

            while self._running:
                try:
                    # รัน Engine Tick
                    self.engine.run_tick()

                    # อัปเดต UI Events
                    self.app.processEvents()

                    # พักตาม tick rate
                    time.sleep(self.engine.get_sleep_time())

                except Exception as e:
                    print(f"⚠️ Error in main loop: {e}")
                    time.sleep(0.1)  # ชะลอถ้ามี error

        except KeyboardInterrupt:
            print("\n👋 ผู้ใช้หยุดโปรแกรม")
        except Exception as e:
            print(f"\n❌ Fatal Error: {e}")
            import traceback

            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        if self.engine:
            try:
                self.engine.cleanup()
            except Exception as e:
                print(f"⚠️ Error during cleanup: {e}")

        if self.app:
            try:
                self.app.quit()
            except:
                pass

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
