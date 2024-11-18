# Базовый образ WireGuard с Python
FROM lscr.io/linuxserver/wireguard:latest

# Установка Python, зависимостей и утилит WireGuard
RUN apk update && apk add --no-cache python3 py3-pip wireguard-tools bash

# Копируем файлы приложения
COPY app.py /app/app.py
COPY requirements.txt /app/requirements.txt
COPY templates/ /app/templates/
COPY static/ /app/static/
COPY users.json /etc/wireguard/users.json

# Копируем entrypoint.sh
COPY entrypoint.sh /entrypoint.sh

# Устанавливаем права на выполнение для entrypoint
RUN chmod +x /entrypoint.sh

# Создаем файл конфигурации wg0.conf и генерируем ключи
RUN [ ! -d /etc/wireguard ] || rm -rf /etc/wireguard && \
    mkdir -p /etc/wireguard && \
    WG_PRIVATE_KEY=$(wg genkey) && \
    WG_PUBLIC_KEY=$(echo $WG_PRIVATE_KEY | wg pubkey) && \
    echo "[Interface]" > /etc/wireguard/wg0.conf && \
    echo "Address = 10.8.0.1/24" >> /etc/wireguard/wg0.conf && \
    echo "PrivateKey = $WG_PRIVATE_KEY" >> /etc/wireguard/wg0.conf && \
    echo "ListenPort = 51820" >> /etc/wireguard/wg0.conf && \
    echo "SaveConfig = true" >> /etc/wireguard/wg0.conf

# Создаем виртуальное окружение и устанавливаем Python-зависимости
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Настраиваем рабочую директорию
WORKDIR /app

# Открываем порты
EXPOSE 80
EXPOSE 51820/udp

# Устанавливаем entrypoint
ENTRYPOINT ["/entrypoint.sh"]
