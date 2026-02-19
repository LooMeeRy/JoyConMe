import sys
import time

from PySide6.QtWidgets import QApplication  # ✨ ต้องมีตัวนี้

from engine import JoyConEngine


def main():
    # 1. สร้างบอสใหญ่ของ UI ก่อนเป็นอันดับแรก
    app = QApplication(sys.argv)

    try:
        # 2. สั่งรันเครื่องยนต์
        engine = JoyConEngine()

        print("🚀 ระบบ JoyConMe พร้อมทำงาน... (กด Ctrl+C เพื่อหยุด)")

        while True:
            # รันการคำนวณจอย
            engine.run_tick()

            # ✨ อนุญาตให้ UI อัปเดต (สำคัญมาก!)
            app.processEvents()

            # พักตามรอบความเร็วที่ตั้งไว้
            time.sleep(engine.get_sleep_time())

    except KeyboardInterrupt:
        print("\n👋 ปิดโปรแกรมเรียบร้อย...")
    except Exception as e:
        print(f"❌ เกิดข้อความผิดพลาด: {e}")


if __name__ == "__main__":
    main()
