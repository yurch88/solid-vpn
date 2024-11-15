FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=80
ENV WG_CONFIG_DIR=/etc/wireguard
ENV WG_INTERFACE=wg0

EXPOSE 80

CMD ["flask", "run"]
