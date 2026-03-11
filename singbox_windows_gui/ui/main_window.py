import os
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'D:\MyProxy\singbox_windows_gui\venv\Lib\site-packages\PyQt5\Qt5\plugins\platforms'
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget
from ui.tabs import InstallTab, SettingsTab, ControlTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sing-box Manager для Windows")
        self.setGeometry(100, 100, 800, 600)

        # Центральный виджет с вкладками
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Создаем вкладки
        self.install_tab = InstallTab()
        self.settings_tab = SettingsTab()
        self.control_tab = ControlTab()

        self.tabs.addTab(self.install_tab, "Установка")
        self.tabs.addTab(self.settings_tab, "Настройки")
        self.tabs.addTab(self.control_tab, "Управление")