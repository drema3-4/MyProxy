import sys
import os
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'D:\MyProxy\singbox_windows_gui\venv\Lib\site-packages\PyQt5\Qt5\plugins\platforms'
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QMessageBox
from ui.tabs import InstallTab, SettingsTab, ControlTab
from core.admin import is_admin, run_as_admin

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sing-Box Manager")
        self.setGeometry(100, 100, 800, 600)

        tabs = QTabWidget()
        tabs.addTab(InstallTab(), "Установка")
        tabs.addTab(SettingsTab(), "Настройки")
        tabs.addTab(ControlTab(), "Управление")

        self.setCentralWidget(tabs)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    if not is_admin():
        reply = QMessageBox.question(
            None,
            "Права администратора",
            "Приложение требует прав администратора для работы с TUN-интерфейсом.\n\n"
            "Перезапустить с правами администратора?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            run_as_admin()
        else:
            QMessageBox.warning(None, "Предупреждение",
                "Приложение будет работать в ограниченном режиме. Запуск прокси может быть невозможен.")

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())