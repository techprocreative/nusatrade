import sys
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


class ForexAIConnectorApp:
    def __init__(self):
        self.qt_app = QApplication(sys.argv)
        self.window = MainWindow()

    def run(self):
        self.window.show()
        sys.exit(self.qt_app.exec())
