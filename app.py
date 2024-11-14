from flask import Flask, render_template, redirect, url_for, request, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import subprocess
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"

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

# Directory to store WireGuard configuration files
WG_CONFIG_DIR = "/etc/wireguard"
USER_DATA_FILE = "/etc/wireguard/users.json"  # File to store user metadata

your_server_public_key = "<YOUR_SERVER_PUBLIC_KEY>"  # Replace with your actual server public key
your_server_ip = "<YOUR_SERVER_IP>"  # Replace with your actual server IP

# Ensure user data file exists
if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "w") as f:
        json.dump({}, f)

def load_user_data():
    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == "password":  # Replace with your secure password validation
            user = User(id=1)
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid password")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    # Load user data
    user_data = load_user_data()
    # Sort users by creation date
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]["created_at"])
    return render_template("dashboard.html", user=current_user, users=sorted_users)

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
        # Load user data
        user_data = load_user_data()

        if username in user_data:
            return "User already exists", 400

        # Generate a new WireGuard configuration for the user
        user_config_path = os.path.join(WG_CONFIG_DIR, f"{username}.conf")

        # Generate the private and public keys for the new user
        private_key = subprocess.check_output(["wg", "genkey"]).decode("utf-8").strip()
        public_key = subprocess.check_output(["wg", "pubkey"], input=private_key.encode("utf-8")).decode("utf-8").strip()

        # Create the WireGuard configuration file
        config = f"""
        [Interface]
        PrivateKey = {private_key}
        Address = 10.0.0.2/32  # You should use a unique address for each user
        DNS = 8.8.8.8

        [Peer]
        PublicKey = {your_server_public_key}
        Endpoint = {your_server_ip}:51820
        AllowedIPs = 0.0.0.0/0, ::/0
        """

        # Write the config to file
        with open(user_config_path, "w") as f:
            f.write(config)

        # Add user metadata
        user_data[username] = {"created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        save_user_data(user_data)

        return redirect(url_for("dashboard"))

    return redirect(url_for("dashboard"))

@app.route("/download_config/<username>")
@login_required
def download_config(username):
    config_path = os.path.join(WG_CONFIG_DIR, f"{username}.conf")
    if os.path.exists(config_path):
        return send_file(config_path, as_attachment=True)
    return "Config file not found", 404

@app.route("/delete_config/<username>", methods=["POST"])
@login_required
def delete_config(username):
    config_path = os.path.join(WG_CONFIG_DIR, f"{username}.conf")
    if os.path.exists(config_path):
        os.remove(config_path)

    # Remove user metadata
    user_data = load_user_data()
    if username in user_data:
        del user_data[username]
        save_user_data(user_data)

    return "Config file deleted", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
