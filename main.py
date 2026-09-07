"""
main.py
========
SILVERLINE Akıllı Fırın Arayüzü - giriş noktası.

Çalıştırma:
    python3 main.py

Jetson TX2'de gerçek donanımla tam ekran kiosk modu için
config.py içinde DEBUG_MODE = False yapın.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

import config
from ui.splash_screen import SplashScreen
from ui.main_window import MainWindow


def load_stylesheet(app):
    qss_path = os.path.join(os.path.dirname(__file__), "styles", "theme.qss")
    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass


def main():
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)
    load_stylesheet(app)

    window = MainWindow()
    splash = SplashScreen()

    # Splash'ten ana ekrana geçerken kısa süreliğine masaüstünün görünmesinin
    # sebebi, splash kapanıp ana pencere gerçekten ekrana "map" edilene kadar
    # geçen küçük boşluk. Bunu önlemek için ana pencereyi EN BAŞTA, splash'in
    # ARKASINDA tam ekran olarak gösteriyoruz; splash kapandığında ana pencere
    # zaten oradadır, araya hiçbir boşluk girmez.
    window.show_kiosk()
    splash.show_kiosk()

    def go_to_main():
        splash.close()
        window.activateWindow()
        window.raise_()
        if not config.DEBUG_MODE:
            # Splash klavye grab'ini bıraktı; ESC'nin kesintisiz çalışması
            # için grab'i ana pencereye geri veriyoruz.
            window.grabKeyboard()

    splash.finished.connect(go_to_main)
    splash.start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
