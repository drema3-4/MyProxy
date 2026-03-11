import os
import zipfile
import requests
import os
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'D:\MyProxy\singbox_windows_gui\venv\Lib\site-packages\PyQt5\Qt5\plugins\platforms'
from PyQt5.QtCore import QObject, pyqtSignal
import shutil

class Installer(QObject):
    # Сигналы для обновления GUI
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)  # процент выполнения
    finished_signal = pyqtSignal(bool, str)  # успех/неудача, сообщение

    def __init__(self, install_path):
        super().__init__()
        self.install_path = install_path
        self.session = requests.Session()

    def get_latest_singbox_version(self):
        """Запрос к GitHub API для получения последней версии и URL скачивания Windows zip"""
        try:
            api_url = "https://api.github.com/repos/SagerNet/sing-box/releases/latest"
            resp = self.session.get(api_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            tag = data['tag_name'].lstrip('v')  # убираем 'v' в начале
            # Ищем ассет с названием, содержащим windows-amd64
            for asset in data['assets']:
                if 'windows-amd64' in asset['name'] and asset['name'].endswith('.zip'):
                    download_url = asset['browser_download_url']
                    return tag, download_url
            raise Exception("Не найден подходящий ассет для Windows")
        except Exception as e:
            self.log_signal.emit(f"Ошибка получения версии sing-box: {e}")
            return None, None

    def download_file(self, url, dest_folder, filename=None):
        """Скачивает файл и сохраняет в dest_folder, возвращает полный путь"""
        if filename is None:
            filename = url.split('/')[-1]
        dest_path = os.path.join(dest_folder, filename)
        os.makedirs(dest_folder, exist_ok=True)

        try:
            self.log_signal.emit(f"Скачивание {filename}...")
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        progress = int((downloaded / total_size) * 100)
                        self.progress_signal.emit(progress)
            self.log_signal.emit(f"Скачивание {filename} завершено.")
            return dest_path
        except Exception as e:
            self.log_signal.emit(f"Ошибка скачивания {filename}: {e}")
            return None

    def extract_zip(self, zip_path, extract_to):
        """Распаковывает zip-архив в указанную папку"""
        try:
            self.log_signal.emit(f"Распаковка {os.path.basename(zip_path)}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            self.log_signal.emit("Распаковка завершена.")
            return True
        except Exception as e:
            self.log_signal.emit(f"Ошибка распаковки: {e}")
            return False

    def download_geoip_geosite(self):
        """Скачивает geoip.db и geosite.db в папку data внутри install_path"""
        data_dir = os.path.join(self.install_path, "data")
        os.makedirs(data_dir, exist_ok=True)

        # Ссылки на последние релизы (можно брать из API, но для простоты фиксируем)
        geoip_url = "https://github.com/SagerNet/sing-geoip/releases/latest/download/geoip.db"
        geosite_url = "https://github.com/SagerNet/sing-geosite/releases/latest/download/geosite.db"

        self.log_signal.emit("Скачивание GeoIP и Geosite...")
        self.progress_signal.emit(0)  # сброс прогресса

        geoip_path = self.download_file(geoip_url, data_dir, "geoip.db")
        if not geoip_path:
            self.finished_signal.emit(False, "Ошибка скачивания geoip.db")
            return

        geosite_path = self.download_file(geosite_url, data_dir, "geosite.db")
        if not geosite_path:
            self.finished_signal.emit(False, "Ошибка скачивания geosite.db")
            return

        self.log_signal.emit("GeoIP и Geosite успешно загружены.")
        self.finished_signal.emit(True, "Установка GeoIP/Geosite завершена.")

    def install_singbox(self):
        """Полный процесс установки sing-box: получение версии, скачивание, распаковка"""
        self.log_signal.emit("Начало установки sing-box...")
        self.progress_signal.emit(0)

        version, download_url = self.get_latest_singbox_version()
        if not version or not download_url:
            self.finished_signal.emit(False, "Не удалось получить версию sing-box")
            return

        self.log_signal.emit(f"Последняя версия: {version}")

        # Скачиваем архив
        zip_path = self.download_file(download_url, self.install_path)
        if not zip_path:
            self.finished_signal.emit(False, "Ошибка скачивания sing-box")
            return

        # Распаковываем
        if not self.extract_zip(zip_path, self.install_path):
            self.finished_signal.emit(False, "Ошибка распаковки sing-box")
            return

        # Удаляем архив (опционально)
        try:
            os.remove(zip_path)
            self.log_signal.emit("Временный архив удалён.")
        except:
            pass

        # Перемещаем sing-box.exe в корень install_path (если он в подпапке)
        # После распаковки обычно создаётся папка типа sing-box-1.x.x-windows-amd64
        # Найдём exe и переместим
        import glob
        exe_pattern = os.path.join(self.install_path, "sing-box-*", "sing-box.exe")
        exe_files = glob.glob(exe_pattern)
        if exe_files:
            src_exe = exe_files[0]
            dst_exe = os.path.join(self.install_path, "sing-box.exe")
            os.rename(src_exe, dst_exe)
            self.log_signal.emit("sing-box.exe перемещён в корневую папку.")
            # Удаляем оставшуюся пустую папку
            shutil.rmtree(os.path.dirname(src_exe), ignore_errors=True)
        else:
            self.log_signal.emit("Не удалось найти sing-box.exe после распаковки. Проверьте вручную.")

        self.log_signal.emit("Установка sing-box завершена.")
        self.finished_signal.emit(True, "sing-box успешно установлен.")