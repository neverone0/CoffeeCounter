import os
import subprocess
import json
import time
from flask import Flask, request, render_template, redirect, url_for, abort
from werkzeug.utils import secure_filename
from functools import wraps


# ------------------- Helper Funcs------------
# Maybe move the functions here to their own files
STATE_FILE = "state.json"
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"mode": "normal", "pending_task": None, "task_args": None}
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

class timer:
    start_time = None
    end_time = None
    ended = None

    def __init__(self, interval, immediate=True):
        self.interval = interval
        self.immediate = immediate
        if self.immediate:
            self.start()

    def start(self):
        self.start_time = time.time()
        self.end_time = self.start_time + self.interval

    def check_timeout(self):
        ctime = time.time()
        timeout = self.end_time <= time.time()
        if timeout:
            self.ended = ctime
        return timeout

    def has_ended(self):
        return (self.ended is not None) or (self.end_time <= time.time())

    def has_started(self):
        return self.start_time is not None

    def end(self):
        self.ended = time.time()


# ========== CONFIG ==========
STATE = load_state()
LOG_FILE = STATE["logfile"]
UPLOAD_FOLDER = STATE["upload_folder"]
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USER = "admin"
ADMIN_PASS = "CoffeeCounter_msrl"   #  Ah yes, CYbeR SeKUrIty
HOST = "0.0.0.0"
PORT = 5000

# Whitelisted admin commands (safer than arbitrary exec)
# Adapt this for correct services
ALLOWED_COMMANDS = {
    "restart_service": ["sudo", "systemctl", "restart", "myapp.service"],
    "check_disk": ["df", "-h"],
    "list_uploads": ["ls", "-al", UPLOAD_FOLDER]
}
# ============================
TEMPLATE = "webgui.html"
app = Flask(__name__, template_folder="html")
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


@app.route("/")
@requires_auth
def index():
    STATE = load_state()
    # show last 100 lines of log
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            log = "".join(lines[-100:])
    else:
        log = "(log file not found)"

    return render_template(
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
    STATE = load_state()

    if "file" not in request.files:
        abort(400)
    f = request.files["file"]
    filename = secure_filename(f.filename)
    if os.path.splitext(filename)[1] != ".csv":
        abort(422)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    f.save(filepath)

    mode_ack_timer = timer(60)
    while not STATE["mode"] == STATE["mode_ack"]:
        STATE = load_state()
        if mode_ack_timer.check_timeout():
            abort(408)
    mode_ack_timer.end()

    STATE["pending_task"] = "update_balances"
    STATE["task_args"] = [filepath]
    save_state(STATE)

    task_resp_timer = timer(300)
    while STATE["task_response"] is None:
        STATE = load_state()
        if task_resp_timer.check_timeout():
            abort(408)
    task_resp_timer.end()

    status, msg = STATE["task_response"]

    # TODO: Handle task responses
    # TODO: Show spinner while loading and running, pre-run summary and post-run summary. Wait for approval each time

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

    return render_template(
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
