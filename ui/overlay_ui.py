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
        self.center_msg = ""

        # ✨ เพิ่มตัวแปรสำหรับ Countdown
        self.timeout_progress = 0.0  # 0.0 - 1.0

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
        radius = 220
        inner_radius = 70
        num_items = len(self.menu_items)

        if num_items == 0:
            return

        angle_step = 360 / num_items

        # Layer 1: Slices
        for i in range(num_items):
            center_angle_qt = 90 - (i * angle_step)
            start_angle = center_angle_qt - (angle_step / 2)

            if i == self.current_selection:
                painter.setBrush(QBrush(QColor(46, 204, 113, 230)))
                painter.setPen(QPen(QColor(255, 255, 255), 3))
            else:
                painter.setBrush(QBrush(QColor(30, 30, 30, 210)))
                painter.setPen(QPen(QColor(100, 100, 100), 1))

            painter.drawPie(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
                int(start_angle * 16),
                int(angle_step * 16),
            )

        # Layer 2: Text
        font_families = ["Segoe UI Emoji", "Tahoma", "DejaVu Sans", "Sans Serif"]
        font = QFont(font_families, 11, QFont.Weight.Bold)
        painter.setFont(font)

        for i in range(num_items):
            mid_angle_rad = math.radians((i * angle_step) - 90)
            text_dist = radius * 0.72

            tx = center.x() + text_dist * math.cos(mid_angle_rad)
            ty = center.y() + text_dist * math.sin(mid_angle_rad)

            text = self.menu_items[i]
            box_w, box_h = 130, 60
            text_box = QRect(int(tx - box_w / 2), int(ty - box_h / 2), box_w, box_h)

            painter.setPen(QColor(0, 0, 0, 255))
            painter.drawText(
                text_box.translated(1, 1),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                text,
            )

            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(
                text_box, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text
            )

        # Layer 3: Center Circle
        painter.setBrush(QBrush(QColor(15, 15, 15, 250)))
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawEllipse(center, inner_radius, inner_radius)

        # ✨ Layer 3.5: Draw Countdown Circle (Timeout Progress)
        if 0.0 < self.timeout_progress < 1.0:
            pen_width = 5
            countdown_radius = inner_radius - 10

            # สีเขียวลดหายไป
            painter.setPen(QPen(QColor(255, 100, 100), pen_width))
            painter.drawEllipse(center, countdown_radius, countdown_radius)

            # สีแดงวิ่งตามเวลา (Start at 12 o'clock: -90 degrees)
            # Qt angle is 1/16th degree.
            span_angle = int(-360 * 16 * self.timeout_progress)
            start_angle = 90 * 16  # 12 o'clock

            painter.setPen(
                QPen(
                    QColor(46, 204, 113),
                    pen_width,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )
            painter.drawArc(
                center.x() - countdown_radius,
                center.y() - countdown_radius,
                countdown_radius * 2,
                countdown_radius * 2,
                start_angle,
                span_angle,
            )

        # Layer 4: Center Text
        if self.center_msg:
            lines = self.center_msg.split("\n")
            painter.setFont(QFont(font_families, 10, QFont.Weight.Bold))
            painter.setPen(QColor(255, 215, 0))
            line1_rect = QRect(
                center.x() - inner_radius, center.y() - 28, inner_radius * 2, 25
            )
            painter.drawText(line1_rect, Qt.AlignmentFlag.AlignCenter, lines[0])

            if len(lines) > 1:
                painter.setFont(QFont(font_families, 9, QFont.Weight.Normal))
                painter.setPen(Qt.GlobalColor.white)
                line2_rect = QRect(
                    center.x() - inner_radius, center.y() + 5, inner_radius * 2, 25
                )
                painter.drawText(line2_rect, Qt.AlignmentFlag.AlignCenter, lines[1])

        elif 0 <= self.current_selection < num_items:
            selected_text = self.menu_items[self.current_selection]
            painter.setFont(QFont(font_families, 10, QFont.Weight.Bold))
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
        adjusted_angle = (angle + (angle_step / 2)) % 360
        new_selection = int(adjusted_angle // angle_step)

        if new_selection != self.current_selection:
            self.current_selection = new_selection
            self.update()
