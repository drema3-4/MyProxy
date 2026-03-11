import os
import json

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "singbox_settings.json")

DEFAULT_SETTINGS = {
    "install_path": "D:\\sing-box",
    "vps_ip": "",
    "port80": 80,
    "port80_password": "",
    "port443": 443,
    "port443_password": ""
}

def load_settings():
    """Загружает настройки из JSON-файла. Если файла нет, возвращает настройки по умолчанию."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Добавляем отсутствующие ключи со значениями по умолчанию
                for key in DEFAULT_SETTINGS:
                    if key not in data:
                        data[key] = DEFAULT_SETTINGS[key]
                return data
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Сохраняет настройки в JSON-файл."""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)