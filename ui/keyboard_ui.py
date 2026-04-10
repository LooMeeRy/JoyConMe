import subprocess

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMainWindow

CHAR_GROUPS = [
    "ABC",
    "DEF",
    "GHI",
    "JKL",
    None,
    "MNO",
    "PQS",
    "TUV",
    "WXYZ",
]

GRID_POS = [
    (0, 0),
    (1, 0),
    (2, 0),
    (0, 1),
    (1, 1),
    (2, 1),
    (0, 2),
    (1, 2),
    (2, 2),
]

_C_BG = QColor(15, 15, 20, 210)
_C_CELL = QColor(28, 30, 38, 220)
_C_SEL = QColor(50, 50, 60, 240)
_C_BORDER = QColor(55, 57, 68, 255)
_C_SEL_BD = QColor(120, 120, 140, 255)
_C_TEXT = QColor(180, 182, 195, 255)
_C_SEL_TXT = QColor(240, 242, 255, 255)
_C_DIM = QColor(70, 72, 85, 255)
_C_DOT_ON = QColor(200, 202, 215, 255)
_C_DOT_OFF = QColor(55, 57, 68, 255)


class KeyboardOverlay(QMainWindow):
    CS = 72
    GAP = 5
    PAD = 12

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JoyConMe_Keyboard")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_X11DoNotAcceptFocus)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.selected_cell = 4
        self.char_index = -1
        self._shift = False

        # force always-on-top ซ้ำทุก 800ms
        self._top_timer = QTimer(self)
        self._top_timer.timeout.connect(self._force_top)
        self._top_timer.start(800)

        # ปรับขนาดหน้าต่างใหม่ให้เป็นสี่เหลี่ยมจัตุรัสพอดีกับ Grid (ตัดส่วนโชว์ตัวอักษรออก)
        total = self.CS * 3 + self.GAP * 2 + self.PAD * 2
        self.resize(total, total)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(150, self._snap_to_corner)
        QTimer.singleShot(300, self._force_top)

    def _snap_to_corner(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.move(1720, 880)
            return
        geo = screen.availableGeometry()
        self.move(geo.right() - self.width() - 18, geo.bottom() - self.height() - 18)

    def _force_top(self):
        """บังคับ always on top ผ่าน wmctrl + Qt raise"""
        self.raise_()
        try:
            subprocess.Popen(
                ["wmctrl", "-r", "JoyConMe_Keyboard", "-b", "add,above"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except:
            pass

    # --- public API ---
    def set_shift(self, is_shift: bool):
        if self._shift != is_shift:
            self._shift = is_shift
            self.update()

    def set_selected_cell(self, idx: int):
        self.selected_cell = idx
        self.char_index = -1
        self.update()

    def set_char_index(self, idx: int):
        self.char_index = idx
        self.update()

    def set_typed_text(self, text: str):
        # ปล่อยว่างไว้เพื่อรับค่าจาก actions/keyboard.py แต่ไม่เอาไปวาดแสดงผล
        pass

    # --- paint ---
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self._draw_panel(p)
        self._draw_grid(p)

    def _draw_panel(self, p):
        p.setBrush(QBrush(_C_BG))
        p.setPen(QPen(_C_BORDER, 1))
        p.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 10, 10)

    def _draw_grid(self, p):
        ox = self.PAD
        oy = self.PAD  # เริ่มวาด Grid ชิดขอบบนได้เลย
        for idx in range(9):
            col, row = GRID_POS[idx]
            x = ox + col * (self.CS + self.GAP)
            y = oy + row * (self.CS + self.GAP)
            self._draw_cell(p, QRect(x, y, self.CS, self.CS), idx)

    def _draw_cell(self, p, r, idx):
        group = CHAR_GROUPS[idx]
        selected = idx == self.selected_cell
        is_mid = group is None

        p.setBrush(QBrush(_C_SEL if selected else _C_CELL))
        p.setPen(QPen(_C_SEL_BD if selected else _C_BORDER, 1))
        p.drawRoundedRect(r, 7, 7)

        if is_mid:
            self._draw_hints(p, r)
            return

        chars = list(group)
        if selected and self.char_index >= 0:
            ch = chars[self.char_index % len(chars)]
            ch = ch.upper() if self._shift else ch.lower()
            p.setFont(QFont("Consolas", 22, QFont.Weight.Bold))
            p.setPen(_C_SEL_TXT)
            p.drawText(
                QRect(r.x(), r.y(), r.width(), r.height() - 14),
                Qt.AlignmentFlag.AlignCenter,
                ch,
            )
            self._draw_dots(p, r, chars, self.char_index % len(chars))
        else:
            text = " ".join(c.upper() if self._shift else c.lower() for c in chars)
            p.setFont(QFont("Consolas", 11))
            p.setPen(_C_TEXT if selected else _C_DIM)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_dots(self, p, r, chars, active):
        n = len(chars)
        ds, gap = 5, 7
        total = n * ds + (n - 1) * gap
        sx = r.center().x() - total // 2
        dy = r.bottom() - 10
        for i in range(n):
            p.setBrush(QBrush(_C_DOT_ON if i == active else _C_DOT_OFF))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(sx + i * (ds + gap), dy, ds, ds)

    def _draw_hints(self, p, r):
        hints = [("A", "sel"), ("X", "del"), ("Y", "spc"), ("B", "ent")]
        p.setFont(QFont("Consolas", 8))
        lh = 14
        sy = r.center().y() - (len(hints) * lh) // 2
        for i, (k, d) in enumerate(hints):
            y = sy + i * lh
            p.setPen(_C_SEL_TXT)
            p.drawText(QRect(r.x() + 6, y, 14, lh), Qt.AlignmentFlag.AlignCenter, k)
            p.setPen(_C_DIM)
            p.drawText(
                QRect(r.x() + 22, y, r.width() - 26, lh),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                d,
            )
