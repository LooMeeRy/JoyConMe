import math
import sys

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMainWindow


class RadialMenuOverlay(QMainWindow):
    def __init__(self, menu_items=None):
        super().__init__()
        # ตั้งค่าหน้าต่างให้โปร่งใส และอยู่บนสุดเสมอ
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.menu_items = menu_items or []
        self.current_selection = 0
        self.center_msg = ""  # เก็บข้อความยืนยันตรงกลาง

        self.resize(800, 800)
        self.center_window()

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        center = QPoint(self.width() // 2, self.height() // 2)
        radius = 220  # รัศมีวงกลมหลัก
        inner_radius = 70  # รัศมีวงกลมตรงกลาง
        num_items = len(self.menu_items)

        if num_items == 0:
            return

        angle_step = 360 / num_items

        # --- Layer 1: วาดพื้นหลัง (Slices) ---
        for i in range(num_items):
            # คำนวณมุมสำหรับ Qt (0 องศาของ Qt คือ 3 นาฬิกา)
            center_angle_qt = 90 - (i * angle_step)
            start_angle = center_angle_qt - (angle_step / 2)

            if i == self.current_selection:
                painter.setBrush(QBrush(QColor(46, 204, 113, 230)))  # สีเขียวเน้นๆ
                painter.setPen(QPen(QColor(255, 255, 255), 3))
            else:
                painter.setBrush(QBrush(QColor(30, 30, 30, 210)))  # สีเทาเข้มใส
                painter.setPen(QPen(QColor(100, 100, 100), 1))

            painter.drawPie(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
                int(start_angle * 16),
                int(angle_step * 16),
            )

        # --- Layer 2: วาดตัวหนังสือรอบวง (ป้องกันการทับกัน) ---
        for i in range(num_items):
            mid_angle_rad = math.radians((i * angle_step) - 90)
            text_dist = radius * 0.72  # วางตำแหน่งตัวหนังสือ

            tx = center.x() + text_dist * math.cos(mid_angle_rad)
            ty = center.y() + text_dist * math.sin(mid_angle_rad)

            text = self.menu_items[i]

            # กำหนดขอบเขตกล่องข้อความรอบแฉกเพื่อทำ Word Wrap
            box_w, box_h = 130, 60
            text_box = QRect(int(tx - box_w / 2), int(ty - box_h / 2), box_w, box_h)

            # ปรับขนาดฟอนต์อัตโนมัติถ้าคำยาว
            f_size = 11 if len(text) < 12 else 9
            font = QFont("Sans Serif", f_size, QFont.Weight.Bold)
            painter.setFont(font)

            # วาดเงาตัวอักษร
            painter.setPen(QColor(0, 0, 0, 255))
            painter.drawText(
                text_box.translated(1, 1),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                text,
            )

            # วาดตัวอักษรสีขาว
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                text_box, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text
            )

        # --- Layer 3: วาดวงกลมตรงกลาง (Dashboard) ---
        painter.setBrush(QBrush(QColor(15, 15, 15, 250)))
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawEllipse(center, inner_radius, inner_radius)

        # วาดข้อความยืนยัน/สถานะ ตรงกลาง (ระบบ 2 บรรทัดแยกกันชัดเจน)
        if self.center_msg:
            lines = self.center_msg.split("\n")

            # บรรทัดที่ 1 (หัวข้อ/ปุ่ม) - สีเหลืองทอง
            painter.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
            painter.setPen(QColor(255, 215, 0))
            line1_rect = QRect(
                center.x() - inner_radius, center.y() - 28, inner_radius * 2, 25
            )
            painter.drawText(line1_rect, Qt.AlignmentFlag.AlignCenter, lines[0])

            # บรรทัดที่ 2 (คำสั่ง) - สีขาวตัวเล็ก
            if len(lines) > 1:
                painter.setFont(QFont("Sans Serif", 9, QFont.Weight.Normal))
                painter.setPen(Qt.GlobalColor.white)
                line2_rect = QRect(
                    center.x() - inner_radius, center.y() + 5, inner_radius * 2, 25
                )
                painter.drawText(line2_rect, Qt.AlignmentFlag.AlignCenter, lines[1])

        elif 0 <= self.current_selection < num_items:
            # โหมดปกติ: แสดงชื่อเมนูที่เลือกอยู่
            selected_text = self.menu_items[self.current_selection]
            painter.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
            painter.setPen(QColor(46, 204, 113))
            center_rect = QRect(
                center.x() - inner_radius + 5,
                center.y() - inner_radius + 5,
                (inner_radius * 2) - 10,
                (inner_radius * 2) - 10,
            )
            painter.drawText(
                center_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                selected_text,
            )

    def update_selection(self, angle):
        num_items = len(self.menu_items)
        if num_items == 0:
            return

        angle_step = 360 / num_items
        # ปรับค่ามุมให้ตรงกับ index (หมุนให้ 0 องศาอยู่บนสุด)
        adjusted_angle = (angle + (angle_step / 2)) % 360
        new_selection = int(adjusted_angle // angle_step)

        if new_selection != self.current_selection:
            self.current_selection = new_selection
            self.update()
