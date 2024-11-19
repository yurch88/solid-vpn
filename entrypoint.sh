#!/bin/bash
set -e

# Загрузка переменных окружения из .env
if [ -f "/app/.env" ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' /app/.env | xargs)
fi

WG_CONFIG_PATH="${WG_CONFIG_DIR}/${WG_INTERFACE}.conf"

# Проверяем переменные окружения
: "${WG_DEFAULT_ADDRESS:?WG_DEFAULT_ADDRESS not set}"
: "${WG_PORT:?WG_PORT not set}"

# Генерация приватного ключа (если не задан в переменных)
if [ -z "$WG_PRIVATE_KEY" ]; then
    echo "Generating WireGuard private key..."
    WG_PRIVATE_KEY=$(wg genkey)
    echo "Generated private key: $WG_PRIVATE_KEY"
fi

# Проверка наличия директории WireGuard
if [ ! -d "$WG_CONFIG_DIR" ]; then
    echo "Creating WireGuard configuration directory..."
    mkdir -p "$WG_CONFIG_DIR"
fi

# Создаём конфигурационный файл WireGuard, если он не существует
if [ ! -f "$WG_CONFIG_PATH" ]; then
    echo "Creating WireGuard configuration at $WG_CONFIG_PATH..."
    echo "[Interface]" > "$WG_CONFIG_PATH"
    echo "Address = $WG_DEFAULT_ADDRESS" >> "$WG_CONFIG_PATH"
    echo "PrivateKey = $WG_PRIVATE_KEY" >> "$WG_CONFIG_PATH"
    echo "ListenPort = $WG_PORT" >> "$WG_CONFIG_PATH"
    echo "SaveConfig = true" >> "$WG_CONFIG_PATH"
    echo "Configuration created successfully."
else
    echo "Configuration file already exists. Skipping creation."
fi

# Устанавливаем правильные права доступа
chmod 600 "$WG_CONFIG_PATH"

# Проверка, существует ли интерфейс wg0
if ip link show "$WG_INTERFACE" &>/dev/null; then
    echo "WireGuard interface $WG_INTERFACE already exists. Skipping activation."
else
    echo "Activating WireGuard interface $WG_INTERFACE..."
    wg-quick up "$WG_CONFIG_PATH"
fi

# Запуск приложения
exec /app/venv/bin/python3 /app/app.py
