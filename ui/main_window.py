"""
ui/main_window.py
====================
Uygulamanın ana penceresi. Sol tarafta NavRail, sağ tarafta QStackedWidget
içinde dört ekran (Ana Ekran, Tarifler, Zamanlayıcı, Ayarlar).

Kiosk davranışı:
  - ESC tuşu -> uygulamayı kapatır (config.DEBUG_MODE farketmeksizin).
  - config.DEBUG_MODE = False iken tam ekran + çerçevesiz + imleç gizli.
"""

from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QApplication, QLabel
from PyQt5.QtCore import Qt, QTimer

import config
from core.oven_controller import OvenController
from core.assistant_bridge import AssistantBridge
from ui.nav_rail import NavRail
from ui.views.home_view import HomeView
from ui.views.recipes_view import RecipesView
from ui.views.timer_view import TimerView
from ui.views.settings_view import SettingsView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SILVERLINE Akıllı Fırın")

        if config.DEBUG_MODE:
            self.setFixedSize(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        else:
            self._enter_kiosk_mode()

        self.controller = OvenController()
        self.assistant = AssistantBridge(self.controller)

        root = QWidget()
        root.setObjectName("root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(root)

        self.nav = NavRail()
        self.nav.view_requested.connect(self._show_view)
        self.nav.mic_pressed.connect(self.assistant.toggle_listening)
        layout.addWidget(self.nav)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, stretch=1)

        self.views = {
            "home": HomeView(self.controller),
            "recipes": RecipesView(self.controller),
            "timer": TimerView(self.controller),
            "settings": SettingsView(self.controller),
        }
        for view in self.views.values():
            self.stack.addWidget(view)

        # Tarif seçilince otomatik ana ekrana dön
        self.views["recipes"].recipe_applied.connect(lambda: self._show_view("home"))

        # Sesli asistan geri bildirim şeridi (transcript/yanıt kısaca gösterilir)
        self.toast = QLabel(self)
        self.toast.setStyleSheet(
            "background-color: rgba(33,31,29,235); color:#f5f1ea; font-size:13px;"
            "border-radius:12px; padding:10px 18px; border:1px solid #3a3532;"
        )
        self.toast.setVisible(False)
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(lambda: self.toast.setVisible(False))

        # Sesli asistan durumuna göre mikrofon ikonunu ve alt bilgi
        # şeridini güncelle (dinliyor / işliyor / konuşuyor).
        self.assistant.state_changed.connect(self.nav.set_mic_state)
        self.assistant.response_ready.connect(self._show_assistant_toast)
        self.assistant.assistant_unavailable.connect(self._on_assistant_unavailable)

        self._show_view("home")

    def _enter_kiosk_mode(self):
        """
        Ubuntu masaüstü ortamında (GNOME/Unity dock'u) showFullScreen()
        çoğu zaman yetmiyor: panel/launcher, pencere yöneticisine ekranın
        bir kısmını (strut) ayırdığını bildiriyor ve WM da bizim pencereyi
        o alanın dışına sıkıştırıyor - "sol taraftaki toolbar açık kalıyor"
        sorununun sebebi bu.

        Kalıcı ve en sağlam çözüm işletim sistemi seviyesinde: Jetson'ı
        bu uygulamayı çalıştıran minimal bir oturumla (openbox/matchbox
        gibi hafif bir WM, ya da doğrudan bu programı autostart eden bir
        X oturumu) açmak - bkz. README "Kiosk kurulumu" bölümü.

        Mevcut Ubuntu masaüstü üzerinde çalışmaya devam etmek gerekiyorsa,
        pencereyi WM'nin strut/karar mekanizmasının tamamen dışına
        (override-redirect) çıkarıp ekranın gerçek piksel boyutuna manuel
        olarak oturtuyoruz. Bu, pencerenin dock'un ÜZERİNDE çizilmesini
        sağlar.
        """
        screen = QApplication.primaryScreen()
        geo = screen.geometry()  # panel/dock'tan etkilenmeyen GERÇEK ekran boyutu

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.X11BypassWindowManagerHint   # WM'i (ve strut kararlarını) devre dışı bırak
            | Qt.WindowStaysOnTopHint
        )
        self.setCursor(Qt.BlankCursor)
        self.setGeometry(geo)
        self.setFixedSize(geo.width(), geo.height())

    def show_kiosk(self):
        """Pencereyi göster ve klavye odağını zorla (ESC her zaman çalışsın)."""
        if config.DEBUG_MODE:
            self.show()
        else:
            self.showFullScreen()
            self.raise_()
            self.activateWindow()
            # X11BypassWindowManagerHint pencereleri bazen otomatik klavye
            # odağı almaz; ESC'nin her koşulda çalışması için klavyeyi
            # doğrudan bu pencereye kilitliyoruz.
            self.grabKeyboard()

    def _show_view(self, key):
        self.stack.setCurrentWidget(self.views[key])
        self.nav.set_active(key)

    def _on_assistant_unavailable(self, message):
        self._show_assistant_toast(message)

    def _show_assistant_toast(self, message):
        self.toast.setText(message)
        self.toast.setVisible(True)
        self.toast.adjustSize()
        self.toast.move(
            (self.width() - self.toast.width()) // 2,
            self.height() - self.toast.height() - 18,
        )
        self.toast.raise_()
        self._toast_timer.start(4000)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close_app()
        else:
            super().keyPressEvent(event)

    def close_app(self):
        if not config.DEBUG_MODE:
            self.releaseKeyboard()
        self.assistant.shutdown()
        self.controller.shutdown()
        QApplication.instance().quit()

    def closeEvent(self, event):
        self.assistant.shutdown()
        self.controller.shutdown()
        super().closeEvent(event)
