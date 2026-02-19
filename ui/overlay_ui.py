import math
import sys

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMainWindow


class RadialMenuOverlay(QMainWindow):
    def __init__(self, menu_items=None):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.menu_items = menu_items or []
        self.current_selection = 0
        self.center_msg = ""  # ✨ เพิ่มตัวแปรเก็บข้อความพิเศษตรงกลาง

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
        radius = 200
        inner_radius = 65
        num_items = len(self.menu_items)
        if num_items == 0:
            return

        angle_step = 360 / num_items
        font = QFont("Sans Serif", 14, QFont.Weight.Bold)
        painter.setFont(font)
        metrics = QFontMetrics(font)

        # Layer 1: พื้นหลัง
        for i in range(num_items):
            center_angle_qt = 90 - (i * angle_step)
            start_angle = center_angle_qt - (angle_step / 2)
            if i == self.current_selection:
                painter.setBrush(QBrush(QColor(46, 204, 113, 220)))
                painter.setPen(QPen(QColor(255, 255, 255), 3))
            else:
                painter.setBrush(QBrush(QColor(40, 40, 40, 200)))
                painter.setPen(QPen(QColor(150, 150, 150), 2))
            painter.drawPie(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
                int(start_angle * 16),
                int(angle_step * 16),
            )

        # Layer 2: ตัวหนังสือรอบวง
        for i in range(num_items):
            mid_angle = math.radians((i * angle_step) - 90)
            text_dist = radius * 0.65
            tx = center.x() + text_dist * math.cos(mid_angle)
            ty = center.y() + text_dist * math.sin(mid_angle)
            text = self.menu_items[i]
            text_rect = metrics.boundingRect(text)
            text_path_rect = QRect(
                int(tx - text_rect.width() / 2),
                int(ty - text_rect.height() / 2),
                text_rect.width(),
                text_rect.height(),
            )
            painter.setPen(QColor(0, 0, 0, 255))
            painter.drawText(
                text_path_rect.translated(2, 2), Qt.AlignmentFlag.AlignCenter, text
            )
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(text_path_rect, Qt.AlignmentFlag.AlignCenter, text)

        # Layer 3: วงกลมตรงกลาง
        painter.setBrush(QBrush(QColor(20, 20, 20, 240)))
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawEllipse(center, inner_radius, inner_radius)

        # ✨ แสดงข้อความตรงกลาง (สลับระหว่างข้อความพิเศษ กับ ชื่อเมนูที่เลือกอยู่)
        center_rect = QRect(
            center.x() - inner_radius + 5,
            center.y() - inner_radius + 5,
            (inner_radius * 2) - 10,
            (inner_radius * 2) - 10,
        )

        if self.center_msg:
            # โหมดโชว์ข้อความยืนยัน (สีเหลืองทอง)
            painter.setFont(QFont("Sans Serif", 10, QFont.Weight.Bold))
            painter.setPen(QColor(255, 215, 0))
            painter.drawText(
                center_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                self.center_msg,
            )
        elif 0 <= self.current_selection < num_items:
            # โหมดปกติ
            selected_text = self.menu_items[self.current_selection]
            painter.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
            painter.setPen(QColor(46, 204, 113))
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
        adjusted_angle = (angle + (angle_step / 2)) % 360
        new_selection = int(adjusted_angle // angle_step)
        if new_selection != self.current_selection:
            self.current_selection = new_selection
            self.update()
