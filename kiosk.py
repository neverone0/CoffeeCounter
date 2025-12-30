import os
import subprocess
import json
from flask import Flask, request, render_template_string, redirect, url_for, abort
from werkzeug.utils import secure_filename
from functools import wraps


# ------------------- Helper Funcs------------
STATE_FILE = "state.json"
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"mode": "normal", "pending_task": None, "task_args": None}
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ========== CONFIG ==========
STATE = load_state()
LOG_FILE = STATE["logfile"]
UPLOAD_FOLDER = STATE["upload_folder"]
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USER = "admin"
ADMIN_PASS = "CoffeeCounter_msrl"   #  Ah yes, CYbeR SeKUrIty
HOST = "0.0.0.0" # CHANGE THIS TO 127.0.0.0 such that only displayed on pi
PORT = 7000

# Whitelisted admin commands (safer than arbitrary exec)
ALLOWED_COMMANDS = {
    "restart_service": ["sudo", "systemctl", "restart", "myapp.service"],
    "check_disk": ["df", "-h"],
    "list_uploads": ["ls", "-al", UPLOAD_FOLDER]
}
# ============================

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------- BASIC AUTH ----------
def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS


def authenticate():
    return ("Authentication required", 401,
            {"WWW-Authenticate": 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# ---------- PAGES ----------
TEMPLATE = """
<!doctype html>
<html>
<head>
<title>Raspberry Pi Admin</title>
<style>
body{font-family:Arial;margin:20px}
pre{background:#111;color:#0f0;padding:10px}
.card{border:1px solid #ccc;margin-bottom:20px;padding:10px}
</style>
</head>
<body>
<h1>Raspberry Pi Admin Panel</h1>

<div class="card">
<h3>Log Viewer</h3>
<pre>{{ log }}</pre>
</div>

<div class="card">
<h3>Upload File</h3>
<form method="post" enctype="multipart/form-data" action="{{ url_for('upload') }}">
<input type="file" name="file">
<button type="submit">Upload</button>
</form>
<p>Uploaded files are stored in: {{ upload_folder }}</p>
</div>

<div class="card">
<h3>Admin Actions</h3>
<form method="post" action="{{ url_for('toggle_mode') }}">
<button>
{% if mode == "normal" %}Enable Maintenance{% else %}Disable Maintenance{% endif %}
</button>
</form>
<p>Current mode: <b>{{ mode }}</b></p>
<form method="post" action="{{ url_for('run_command') }}">
<select name="command">
{% for cmd in commands %}
<option value="{{ cmd }}">{{ cmd }}</option>
{% endfor %}
</select>
<button type="submit">Run</button>
</form>
<pre>{{ command_output }}</pre>
</div>

</body>
</html>

"""


@app.route("/")
@requires_auth
def index():
    # show last 200 lines of log
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            log = "".join(lines[-200:])
    else:
        log = "(log file not found)"

    return render_template_string(
        TEMPLATE,
        log=log,
        mode=STATE["mode"],
        commands=ALLOWED_COMMANDS.keys(),
        command_output="",
        upload_folder=UPLOAD_FOLDER
    )


@app.route("/upload", methods=["POST"])
@requires_auth
def upload():
    if "file" not in request.files:
        abort(400)

    f = request.files["file"]
    filename = secure_filename(f.filename)
    f.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    return redirect(url_for("index"))


@app.route("/run", methods=["POST"])
@requires_auth
def run_command():
    cmd_key = request.form.get("command")

    if cmd_key not in ALLOWED_COMMANDS:
        abort(400)

    try:
        result = subprocess.check_output(
            ALLOWED_COMMANDS[cmd_key],
            stderr=subprocess.STDOUT,
            text=True
        )
    except subprocess.CalledProcessError as e:
        result = e.output

    # reload page with output
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            log = "".join(f.readlines()[-200:])
    else:
        log = "(log file not found)"

    return render_template_string(
        TEMPLATE,
        log=log,
        commands=ALLOWED_COMMANDS.keys(),
        command_output=result,
        upload_folder=UPLOAD_FOLDER
    )

@app.route("/toggle_mode", methods=["POST"])
@requires_auth
def toggle_mode():
    STATE = load_state()

    if STATE["mode"] == "normal":
        STATE["mode"] = "maintenance"
    else:
        STATE["mode"] = "normal"
        STATE["pending_task"] = None
        STATE["task_args"] = None

    save_state(STATE)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)
