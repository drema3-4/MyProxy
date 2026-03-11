import os
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'D:\MyProxy\singbox_windows_gui\venv\Lib\site-packages\PyQt5\Qt5\plugins\platforms'
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QProgressBar, QTextEdit,
                             QFileDialog, QMessageBox, QGroupBox, QFormLayout)
from PyQt5.QtCore import QThread, QProcess, QProcessEnvironment
from PyQt5.QtGui import QColor
from core.settings import load_settings, save_settings
import json
from core.installer import Installer
from core.admin import is_admin, run_as_admin

class WorkerThread(QThread):
    """Поток для выполнения установки без блокировки GUI"""
    def __init__(self, installer, operation):
        super().__init__()
        self.installer = installer
        self.operation = operation  # 'install' или 'geo'

    def run(self):
        if self.operation == 'install':
            self.installer.install_singbox()
        elif self.operation == 'geo':
            self.installer.download_geoip_geosite()

class InstallTab(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()  # загружаем настройки
        self.install_path = self.settings.get("install_path", "D:\\sing-box")
        self.thread = None
        self.installer = None
        self.init_ui()
  
    def on_path_changed(self, text):
        self.install_path = text
        settings = load_settings()
        settings["install_path"] = text
        save_settings(settings)

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Строка выбора папки
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Папка установки:"))
        self.path_edit = QLineEdit(self.install_path)
        path_layout.addWidget(self.path_edit)
        self.browse_btn = QPushButton("Обзор")
        self.browse_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.browse_btn)
        main_layout.addLayout(path_layout)

        # Кнопки действий
        btn_layout = QHBoxLayout()
        self.install_btn = QPushButton("Скачать и установить sing-box")
        self.install_btn.clicked.connect(self.start_install)
        btn_layout.addWidget(self.install_btn)

        self.geo_btn = QPushButton("Скачать GeoIP и Geosite")
        self.geo_btn.clicked.connect(self.start_geo_download)
        btn_layout.addWidget(self.geo_btn)
        main_layout.addLayout(btn_layout)

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setValue(0)
        main_layout.addWidget(self.progress)

        # Лог
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        main_layout.addWidget(self.log)

        self.setLayout(main_layout)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для установки")
        if folder:
            self.install_path = folder
            self.path_edit.setText(folder)
            # Сохраняем путь в настройки
            self.settings["install_path"] = folder
            save_settings(self.settings)

    def log_message(self, msg):
        self.log.append(msg)

    def update_progress(self, value):
        self.progress.setValue(value)

    def on_finished(self, success, message):
        self.install_btn.setEnabled(True)
        self.geo_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.path_edit.setEnabled(True)
        if success:
            QMessageBox.information(self, "Успех", message)
        else:
            QMessageBox.critical(self, "Ошибка", message)
        self.thread = None
        self.installer = None

    def start_install(self):
        # Проверяем, не запущен ли уже процесс
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Внимание", "Установка уже выполняется")
            return

        self.install_path = self.path_edit.text()
        if not os.path.exists(self.install_path):
            try:
                os.makedirs(self.install_path)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать папку: {e}")
                return

        # Блокируем кнопки
        self.install_btn.setEnabled(False)
        self.geo_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.path_edit.setEnabled(False)
        self.progress.setValue(0)
        self.log.clear()

        # Создаём объект установщика и перемещаем в поток
        self.installer = Installer(self.install_path)
        self.installer.log_signal.connect(self.log_message)
        self.installer.progress_signal.connect(self.update_progress)
        self.installer.finished_signal.connect(self.on_finished)

        self.thread = WorkerThread(self.installer, 'install')
        self.thread.start()

    def start_geo_download(self):
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Внимание", "Операция уже выполняется")
            return

        self.install_path = self.path_edit.text()
        if not os.path.exists(self.install_path):
            QMessageBox.critical(self, "Ошибка", "Сначала выберите существующую папку установки")
            return

        self.install_btn.setEnabled(False)
        self.geo_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.path_edit.setEnabled(False)
        self.progress.setValue(0)
        self.log.clear()

        self.installer = Installer(self.install_path)
        self.installer.log_signal.connect(self.log_message)
        self.installer.progress_signal.connect(self.update_progress)
        self.installer.finished_signal.connect(self.on_finished)

        self.thread = WorkerThread(self.installer, 'geo')
        self.thread.start()

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.init_ui()
        self.load_settings_to_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Группа параметров VPS
        vps_group = QGroupBox("Параметры VPS")
        form_layout = QFormLayout()

        self.ip_edit = QLineEdit()
        form_layout.addRow("IP адрес VPS:", self.ip_edit)

        self.pass80_edit = QLineEdit()
        self.pass80_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Пароль для порта 80:", self.pass80_edit)

        self.pass443_edit = QLineEdit()
        self.pass443_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Пароль для порта 443:", self.pass443_edit)

        vps_group.setLayout(form_layout)
        main_layout.addWidget(vps_group)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить настройки")
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)

        self.generate_btn = QPushButton("Сгенерировать config.json")
        self.generate_btn.clicked.connect(self.generate_config)
        btn_layout.addWidget(self.generate_btn)

        main_layout.addLayout(btn_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def load_settings_to_ui(self):
        self.ip_edit.setText(self.settings.get("vps_ip", ""))
        self.pass80_edit.setText(self.settings.get("port80_password", ""))
        self.pass443_edit.setText(self.settings.get("port443_password", ""))

    def save_settings(self):
        self.settings["vps_ip"] = self.ip_edit.text().strip()
        self.settings["port80_password"] = self.pass80_edit.text()
        self.settings["port443_password"] = self.pass443_edit.text()
        # Сохраняем порты (можно оставить фиксированными)
        self.settings["port80"] = 80
        self.settings["port443"] = 443

        save_settings(self.settings)
        QMessageBox.information(self, "Успех", "Настройки сохранены.")

    def generate_config(self):
        """Генерирует файл config.json в папке установки на основе текущих настроек."""
        # Проверим, что IP и пароли заполнены
        if not self.settings.get("vps_ip"):
            QMessageBox.warning(self, "Предупреждение", "Сначала укажите IP адрес VPS и сохраните настройки.")
            return

        install_path = self.settings.get("install_path")
        if not install_path or not os.path.exists(install_path):
            QMessageBox.critical(self, "Ошибка", "Папка установки не найдена. Сначала выполните установку на вкладке 'Установка'.")
            return

        # Шаблон конфигурации из PDF
        config = {
            "log": {
                "level": "info",
                "output": "sing-box.log"
            },
            "dns": {
                "servers": [
                    {
                        "tag": "dns-direct",
                        "address": "https://1.1.1.1/dns-query",
                        "strategy": "ipv4_only",
                        "detour": "direct"
                    },
                    {
                        "tag": "dns-proxy",
                        "address": "https://1.1.1.1/dns-query",
                        "strategy": "ipv4_only",
                        "detour": "proxy"
                    }
                ],
                "rules": [
                    {
                        "outbound": "any",
                        "server": "dns-direct"
                    },
                    {
                        "rule_set": [
                            "geosite-google",
                            "geosite-youtube",
                            "geosite-openai",
                            "geosite-anthropic"
                        ],
                        "server": "dns-proxy"
                    }
                ],
                "final": "dns-direct",
                "strategy": "ipv4_only"
            },
            "inbounds": [
                {
                    "type": "tun",
                    "interface_name": "sing-box",
                    "address": "172.19.0.1/30",
                    "mtu": 9000,
                    "auto_route": True,
                    "strict_route": False
                }
            ],
            "outbounds": [
                {
                    "type": "shadowsocks",
                    "tag": "proxy",
                    "server": self.settings["vps_ip"],
                    "server_port": self.settings["port443"],
                    "method": "2022-blake3-aes-128-gcm",
                    "password": self.settings["port443_password"]
                },
                {
                    "type": "direct",
                    "tag": "direct"
                }
            ],
            "route": {
                "default_domain_resolver": "dns-direct",
                "rules": [
                    {
                        "protocol": "dns",
                        "action": "hijack-dns"
                    },
                    {
                        "ip_is_private": True,
                        "outbound": "direct"
                    },
                    {
                        "rule_set": [
                            "geosite-google",
                            "geosite-youtube",
                            "geosite-openai",
                            "geosite-anthropic"
                        ],
                        "outbound": "proxy"
                    },
                    {
                        "rule_set": ["geoip-ru"],
                        "outbound": "direct"
                    }
                ],
                "final": "proxy",
                "auto_detect_interface": True,
                "rule_set": [
                    {
                        "tag": "geosite-google",
                        "type": "remote",
                        "format": "binary",
                        "url": "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-google.srs",
                        "download_detour": "direct"
                    },
                    {
                        "tag": "geosite-youtube",
                        "type": "remote",
                        "format": "binary",
                        "url": "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-youtube.srs",
                        "download_detour": "direct"
                    },
                    {
                        "tag": "geosite-openai",
                        "type": "remote",
                        "format": "binary",
                        "url": "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-openai.srs",
                        "download_detour": "direct"
                    },
                    {
                        "tag": "geosite-anthropic",
                        "type": "remote",
                        "format": "binary",
                        "url": "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-anthropic.srs",
                        "download_detour": "direct"
                    },
                    {
                        "tag": "geoip-ru",
                        "type": "remote",
                        "format": "binary",
                        "url": "https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/geoip-ru.srs",
                        "download_detour": "direct"
                    }
                ]
            }
        }

        config_path = os.path.join(install_path, "config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Успех", f"config.json успешно создан в {config_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось записать config.json: {e}")

class ControlTab(QWidget):
    def __init__(self):
        super().__init__()
        self.process = None
        self.init_ui()
        self.update_status()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Верхняя панель с кнопками и индикатором
        top_layout = QHBoxLayout()

        self.start_btn = QPushButton("Запустить прокси")
        self.start_btn.clicked.connect(self.start_proxy)
        top_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.clicked.connect(self.stop_proxy)
        self.stop_btn.setEnabled(False)
        top_layout.addWidget(self.stop_btn)

        self.open_log_btn = QPushButton("Открыть папку с логами")
        self.open_log_btn.clicked.connect(self.open_log_folder)
        top_layout.addWidget(self.open_log_btn)

        top_layout.addStretch()

        # Индикатор статуса
        self.status_label = QLabel("Статус: Остановлен")
        self.status_label.setAutoFillBackground(True)
        self.set_status_color(False)  # красный
        top_layout.addWidget(self.status_label)

        main_layout.addLayout(top_layout)

        # Область логов
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        main_layout.addWidget(self.log_text)

        self.setLayout(main_layout)

    def set_status_color(self, running):
        palette = self.status_label.palette()
        if running:
            color = QColor(144, 238, 144)  # светло-зелёный
            self.status_label.setText("Статус: Работает")
        else:
            color = QColor(255, 200, 200)  # светло-красный
            self.status_label.setText("Статус: Остановлен")
        palette.setColor(self.status_label.backgroundRole(), color)
        self.status_label.setPalette(palette)

    def log(self, message):
        self.log_text.append(message)
        # Прокручиваем вниз
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def start_proxy(self):
        if self.process and self.process.state() == QProcess.Running:
            QMessageBox.warning(self, "Внимание", "Процесс уже запущен")
            return

        settings = load_settings()
        install_path = settings.get("install_path", "D:\\sing-box")
        exe_path = os.path.join(install_path, "sing-box.exe")
        config_path = os.path.join(install_path, "config.json")

        if not os.path.exists(exe_path):
            QMessageBox.critical(self, "Ошибка", f"sing-box.exe не найден по пути {exe_path}. Выполните установку.")
            return
        if not os.path.exists(config_path):
            QMessageBox.critical(self, "Ошибка", f"config.json не найден по пути {config_path}. Сгенерируйте его на вкладке 'Настройки'.")
            return
        
        if not is_admin():
            reply = QMessageBox.question(
                self,
                "Права администратора",
                "Для запуска прокси необходимы права администратора.\n\nПерезапустить приложение с правами администратора?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                run_as_admin()
            return

        # Создаём процесс
        self.process = QProcess()
        self.process.setProgram(exe_path)
        self.process.setArguments(["run", "-c", config_path])

        # Устанавливаем переменные окружения
        env = QProcessEnvironment.systemEnvironment()
        env.insert("ENABLE_DEPRECATED_LEGACY_DNS_SERVERS", "true")
        env.insert("ENABLE_DEPRECATED_OUTBOUND_DNS_RULE_ITEM", "true")
        env.insert("ENABLE_DEPRECATED_MISSING_DOMAIN_RESOLVER", "true")
        self.process.setProcessEnvironment(env)

        # Подключаем сигналы
        self.process.readyReadStandardOutput.connect(self.on_stdout)
        self.process.readyReadStandardError.connect(self.on_stderr)
        self.process.finished.connect(self.on_finished)

        # Запускаем
        self.process.start()
        if self.process.waitForStarted(3000):
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.set_status_color(True)
            self.log("Процесс запущен.")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось запустить процесс.")
            self.process = None

    def on_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='ignore')
        self.log(text)

    def on_stderr(self):
        data = self.process.readAllStandardError()
        text = bytes(data).decode('utf-8', errors='ignore')
        self.log("[STDERR] " + text)

    def on_finished(self, exit_code, exit_status):
        self.log(f"Процесс завершён с кодом {exit_code}.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.set_status_color(False)
        self.process = None

    def stop_proxy(self):
        if self.process and self.process.state() == QProcess.Running:
            self.process.terminate()
            # Если не завершится за 3 секунды, убиваем принудительно
            if not self.process.waitForFinished(3000):
                self.process.kill()
                self.log("Процесс принудительно завершён.")
        else:
            self.log("Нет запущенного процесса.")

    def open_log_folder(self):
        settings = load_settings()
        install_path = settings.get("install_path", "D:\\sing-box")
        if os.path.exists(install_path):
            os.startfile(install_path)
        else:
            QMessageBox.warning(self, "Предупреждение", f"Папка {install_path} не существует")

    def update_status(self):
        # Можно вызывать периодически или при активации вкладки
        if self.process and self.process.state() == QProcess.Running:
            self.set_status_color(True)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.set_status_color(False)
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)