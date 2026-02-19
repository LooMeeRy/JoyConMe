import os
import time

from engine import InputEngine

# ปิดหน้าต่าง Pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"


def main():
    # สร้าง instance ของระบบ
    engine = InputEngine()

    print("🚀 ระบบ JoyConMe พร้อมทำงาน... (กด Ctrl+C เพื่อหยุด)")

    try:
        while True:
            # สั่งให้ระบบทำงาน 1 รอบ
            engine.run_tick()

            # หน่วงเวลาตามที่ตั้งค่าไว้ใน Config
            time.sleep(engine.get_sleep_time())

    except KeyboardInterrupt:
        print("\n🛑 หยุดการทำงาน")


if __name__ == "__main__":
    main()
