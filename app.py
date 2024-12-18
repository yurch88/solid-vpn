from flask import Flask, render_template, redirect, url_for, request, send_file, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import os
import subprocess
import json
from datetime import datetime

# Загрузка переменных из .env файла
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Mock user for authentication
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Параметры WireGuard из .env
WG_CONFIG_DIR = os.getenv("WG_CONFIG_DIR")
WG_INTERFACE = os.getenv("WG_INTERFACE")
WG_PORT = os.getenv("WG_PORT")
WG_HOST = os.getenv("WG_HOST")
WG_ALLOWED_IPS = os.getenv("WG_ALLOWED_IPS")
WG_DNS = os.getenv("WG_DNS")
USER_DATA_FILE = os.path.join(WG_CONFIG_DIR, "users.json")

# Проверка наличия файла для данных пользователей
if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "w") as f:
        json.dump({}, f)

def load_user_data():
    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_server_info():
    try:
        output = subprocess.check_output(["wg", "show"], text=True, stderr=subprocess.DEVNULL)
        lines = output.splitlines()
        server_info = {}
        for line in lines:
            if "interface:" in line:
                server_info["interface"] = line.split("interface:")[1].strip()
            if "public key:" in line:
                server_info["public_key"] = line.split("public key:")[1].strip()
        with open(f"{WG_CONFIG_DIR}/{WG_INTERFACE}.conf", "r") as f:
            for line in f:
                if "Address" in line:
                    server_info["address"] = line.split("=")[1].strip()
                if "ListenPort" in line:
                    server_info["port"] = line.split("=")[1].strip()
                if "AllowedIPs" in line:
                    server_info["allowed_ips"] = line.split("=")[1].strip()
                if "DNS" in line:
                    server_info["dns"] = line.split("=")[1].strip()
        server_info["allowed_ips"] = server_info.get("allowed_ips", WG_ALLOWED_IPS)
        server_info["dns"] = server_info.get("dns", WG_DNS)
        return server_info
    except Exception as e:
        print(f"Error getting server info: {e}")
        return None

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == os.getenv("FLASK_LOGIN_PASSWORD"):  # Проверяем пароль из .env
            user = User(id=1)
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid password")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user_data = load_user_data()
    server_info = get_server_info()
    return render_template(
        "dashboard.html", user=current_user, users=user_data.items(), server_info=server_info
    )

@app.route("/get_users")
@login_required
def get_users():
    user_data = load_user_data()
    return jsonify(user_data)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/add_user", methods=["POST"])
@login_required
def add_user():
    username = request.form.get("username")
    if username:
        user_data = load_user_data()
        if username in user_data:
            return jsonify({"status": "error", "message": "User already exists"}), 400

        private_key = subprocess.check_output(["wg", "genkey"]).decode("utf-8").strip()
        public_key = subprocess.check_output(
            ["wg", "pubkey"], input=private_key.encode("utf-8")
        ).decode("utf-8").strip()
        preshared_key = subprocess.check_output(["wg", "genpsk"]).decode("utf-8").strip()

        server_info = get_server_info()
        if not server_info:
            return jsonify({"status": "error", "message": "Server not configured"}), 500

        client_config = f"""[Interface]
PrivateKey = {private_key}
Address = {server_info['address']}
DNS = {server_info['dns']}

[Peer]
PublicKey = {server_info['public_key']}
PresharedKey = {preshared_key}
Endpoint = {WG_HOST}:{server_info['port']}
AllowedIPs = {server_info['allowed_ips']}
PersistentKeepalive = 25
"""

        user_config_path = os.path.join(WG_CONFIG_DIR, f"{username}.conf")
        with open(user_config_path, "w") as f:
            f.write(client_config)

        user_data[username] = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "config_path": user_config_path,
            "active": True
        }
        save_user_data(user_data)

        return jsonify({"status": "success", "user": (username, user_data[username])})
    return jsonify({"status": "error", "message": "Invalid username"}), 400

@app.route("/toggle_user/<username>", methods=["POST"])
@login_required
def toggle_user(username):
    user_data = load_user_data()
    if username in user_data:
        current_status = user_data[username].get("active", True)
        user_data[username]["active"] = not current_status
        save_user_data(user_data)
        return jsonify({"status": "success", "active": user_data[username]["active"]})
    return jsonify({"status": "error", "message": "User not found"}), 404

@app.route("/download_config/<username>")
@login_required
def download_config(username):
    user_data = load_user_data()
    if username in user_data:
        config_path = user_data[username].get("config_path")
        if config_path and os.path.exists(config_path):
            return send_file(config_path, as_attachment=True)
    return "Config file not found", 404

@app.route("/delete_config/<username>", methods=["POST"])
@login_required
def delete_config(username):
    user_data = load_user_data()
    if username in user_data:
        config_path = user_data[username].get("config_path")
        if config_path and os.path.exists(config_path):
            os.remove(config_path)
        del user_data[username]
        save_user_data(user_data)
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)
