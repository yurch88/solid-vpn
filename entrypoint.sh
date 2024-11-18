#!/bin/bash
set -e

WG_CONFIG_PATH="/etc/wireguard/wg0.conf"

# Проверка наличия конфигурации WireGuard
if [ ! -f "$WG_CONFIG_PATH" ]; then
    echo "Configuration file not found: $WG_CONFIG_PATH"
    exit 1
fi

# Установка корректных прав доступа к конфигурации
chmod 600 "$WG_CONFIG_PATH"

# Проверка, существует ли интерфейс wg0
if ip link show wg0 &>/dev/null; then
    echo "WireGuard interface wg0 already exists. Skipping activation."
else
    echo "Activating WireGuard interface wg0..."
    wg-quick up "$WG_CONFIG_PATH"
fi

# Запуск приложения
exec /app/venv/bin/python3 /app/app.py
