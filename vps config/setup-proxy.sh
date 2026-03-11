#!/bin/bash
set -e  # Прерывать выполнение при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка запуска от root
if [[ $EUID -ne 0 ]]; then
    print_error "Этот скрипт должен запускаться от root (или через sudo)"
    exit 1
fi

print_info "Начинаем настройку прокси-сервера с sing-box..."

# 1. Обновление системы и установка необходимых пакетов
print_info "Обновление списка пакетов и установка утилит..."
apt update && apt upgrade -y
apt install -y curl wget unzip ufw

# 2. Настройка файрвола
print_info "Настройка UFW (открываем порты 22, 80, 443)..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable   # --force чтобы не спрашивать подтверждения
print_info "UFW включён и настроен."

# 3. Определение последней версии sing-box
print_info "Получаем информацию о последней версии sing-box..."
# Пробуем получить через GitHub API, если не получится — используем фиксированную
if ! command -v jq &> /dev/null; then
    apt install -y jq
fi

LATEST_VERSION=$(curl -s https://api.github.com/repos/SagerNet/sing-box/releases/latest | jq -r .tag_name | sed 's/^v//')
if [[ -z "$LATEST_VERSION" || "$LATEST_VERSION" == "null" ]]; then
    print_warn "Не удалось получить последнюю версию, используем v1.13.1 (как в PDF)"
    LATEST_VERSION="1.13.1"
fi
print_info "Последняя версия: $LATEST_VERSION"

# Определение архитектуры (предполагаем amd64, можно расширить)
ARCH="amd64"
DOWNLOAD_URL="https://github.com/SagerNet/sing-box/releases/download/v${LATEST_VERSION}/sing-box-${LATEST_VERSION}-linux-${ARCH}.tar.gz"

# 4. Скачивание и установка sing-box
print_info "Скачивание sing-box версии $LATEST_VERSION..."
wget -O /tmp/sing-box.tar.gz "$DOWNLOAD_URL"

print_info "Распаковка архива..."
tar -xzf /tmp/sing-box.tar.gz -C /tmp/

print_info "Перемещение бинарника в /usr/local/bin/..."
mv /tmp/sing-box-${LATEST_VERSION}-linux-${ARCH}/sing-box /usr/local/bin/

print_info "Очистка временных файлов..."
rm -rf /tmp/sing-box.tar.gz /tmp/sing-box-${LATEST_VERSION}-linux-${ARCH}/

# Проверка установки
if ! command -v sing-box &> /dev/null; then
    print_error "sing-box не установлен!"
    exit 1
fi
print_info "sing-box успешно установлен: $(sing-box version | head -n1)"

# 5. Генерация паролей для Shadowsocks
print_info "Генерация двух случайных паролей (метод 2022-blake3-aes-128-gcm)..."
PASSWORD1=$(openssl rand -base64 16)
PASSWORD2=$(openssl rand -base64 16)
print_info "Пароль для порта 80: $PASSWORD1"
print_info "Пароль для порта 443: $PASSWORD2"

# 6. Создание конфигурационного файла
print_info "Создание конфигурации /etc/sing-box/config.json..."
mkdir -p /etc/sing-box

cat > /etc/sing-box/config.json <<EOF
{
  "log": {
    "level": "info",
    "output": "/var/log/sing-box.log"
  },
  "inbounds": [
    {
      "type": "shadowsocks",
      "listen": "::",
      "listen_port": 80,
      "method": "2022-blake3-aes-128-gcm",
      "password": "${PASSWORD1}"
    },
    {
      "type": "shadowsocks",
      "listen": "::",
      "listen_port": 443,
      "method": "2022-blake3-aes-128-gcm",
      "password": "${PASSWORD2}"
    }
  ],
  "outbounds": [
    {
      "type": "direct"
    }
  ]
}
EOF

print_info "Конфигурация сохранена."

# 7. Создание systemd-сервиса
print_info "Создание systemd-юнита для автозапуска..."
cat > /etc/systemd/system/sing-box.service <<EOF
[Unit]
Description=sing-box service
Documentation=https://sing-box.sagernet.org
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/sing-box run -c /etc/sing-box/config.json
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

print_info "Перезагрузка systemd и включение сервиса..."
systemctl daemon-reload
systemctl enable sing-box
systemctl start sing-box

# 8. Проверка статуса
print_info "Проверка статуса сервиса:"
if systemctl is-active --quiet sing-box; then
    print_info "sing-box успешно запущен!"
else
    print_error "Сервис не запустился. Проверьте журнал: journalctl -u sing-box -n 50"
    exit 1
fi

print_info "Проверка открытых портов (должны быть 80 и 443):"
ss -tulpn | grep -E ':(80|443)\s'

# 9. Вывод итоговой информации для подключения
IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "НЕ УДАЛОСЬ ОПРЕДЕЛИТЬ")
print_info "=================================================="
print_info "Прокси-сервер настроен и готов к использованию!"
print_info "IP сервера: $IP"
print_info "Порты: 80 и 443"
print_info "Метод шифрования: 2022-blake3-aes-128-gcm"
print_info "Пароль для порта 80: $PASSWORD1"
print_info "Пароль для порта 443: $PASSWORD2"
print_info "=================================================="
print_warn "Сохраните эти пароли в надёжном месте! Они больше не будут показаны."