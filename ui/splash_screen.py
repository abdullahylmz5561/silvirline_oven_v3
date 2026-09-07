"""
ui/splash_screen.py
=====================
Cihaz açılışında görünen "SILVERLINE" animasyonu.
Harf harf beliren logo + altında genişleyen kor renginde bir çizgi.
Animasyon bitince `finished` sinyali yayınlanır.
"""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont

import config


class _UnderlineBar(QWidget):
    """Logo altında soldan sağa dolan ince kor çizgisi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self.setFixedHeight(3)

    def get_progress(self):
        return self._progress

    def set_progress(self, value):
        self._progress = value
        self.update()

    progress = property(get_progress, set_progress)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(QRectF(0, 0, w, h), QColor("#2a2724"))
        p.fillRect(QRectF(0, 0, w * self._progress, h), QColor("#e8672c"))
        p.end()


class SplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color:#141312;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(18)

        self.title = QLabel("")
        self.title.setAlignment(Qt.AlignCenter)
        font = QFont("Space Grotesk")
        font.setPointSize(40)
        font.setBold(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 10)
        self.title.setFont(font)
        self.title.setStyleSheet("color:#f5f1ea;")
        layout.addWidget(self.title)

        self.bar = _UnderlineBar()
        self.bar.setFixedWidth(220)
        layout.addWidget(self.bar, alignment=Qt.AlignCenter)

        self.sub = QLabel("AKILLI FIRIN SİSTEMİ BAŞLATILIYOR")
        self.sub.setAlignment(Qt.AlignCenter)
        self.sub.setStyleSheet("color:#a89f93; font-size:11px; letter-spacing:2px;")
        layout.addWidget(self.sub)

        self._full_text = config.SPLASH_TEXT
        self._char_index = 0

        self._type_timer = QTimer(self)
        self._type_timer.timeout.connect(self._type_next_char)

        self._bar_anim = QPropertyAnimation(self.bar, b"progress")
        self._bar_anim.setStartValue(0.0)
        self._bar_anim.setEndValue(1.0)
        self._bar_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._exit_timer = QTimer(self)
        self._exit_timer.setSingleShot(True)
        self._exit_timer.timeout.connect(self.finished.emit)

    def show_kiosk(self):
        """Ana penceredeki (main_window.show_kiosk) ile aynı mantık: dock/panel
        strut'unu görmezden gelip ekranın gerçek boyutuna oturt."""
        if config.DEBUG_MODE:
            self.setFixedSize(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
            self.show()
            return
        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.X11BypassWindowManagerHint
            | Qt.WindowStaysOnTopHint
        )
        self.setGeometry(geo)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.grabKeyboard()

    def close(self):
        if not config.DEBUG_MODE:
            try:
                self.releaseKeyboard()
            except Exception:
                pass
        return super().close()

    def start(self):
        type_duration = int(config.SPLASH_DURATION_MS * 0.45)
        char_interval = max(30, type_duration // max(1, len(self._full_text)))
        self._type_timer.start(char_interval)

        self._bar_anim.setDuration(int(config.SPLASH_DURATION_MS * 0.7))
        QTimer.singleShot(int(config.SPLASH_DURATION_MS * 0.25), self._bar_anim.start)

        self._exit_timer.start(config.SPLASH_DURATION_MS)

    def _type_next_char(self):
        self._char_index += 1
        self.title.setText(self._full_text[: self._char_index])
        if self._char_index >= len(self._full_text):
            self._type_timer.stop()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            from PyQt5.QtWidgets import QApplication
            QApplication.instance().quit()
        else:
            super().keyPressEvent(event)
