import os
import secrets
from datetime import datetime, timezone
from math import asin, cos, isfinite, radians, sin, sqrt

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, db
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "geosync-default-session-secret")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL")
FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "serviceAccountKey.json")

if not API_KEY:
    raise RuntimeError("API_KEY belum diset di file .env (lihat .env.example).")

if not FIREBASE_DB_URL:
    raise RuntimeError("FIREBASE_DB_URL belum diset di file .env (lihat .env.example).")

resolved_cred_path = (
    FIREBASE_CRED_PATH
    if os.path.isabs(FIREBASE_CRED_PATH)
    else os.path.join(BASE_DIR, FIREBASE_CRED_PATH)
)

if not os.path.isfile(resolved_cred_path):
    raise RuntimeError(
        f"File kredensial Firebase tidak ditemukan di: {resolved_cred_path}"
    )

if not firebase_admin._apps:
    cred = credentials.Certificate(resolved_cred_path)
    firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

TELEMETRY_RULES = {
    "engine_temp_c": (-20.0, 150.0),
    "rpm": (0.0, 3000.0),
    "latitude": (-90.0, 90.0),
    "longitude": (-180.0, 180.0),
    "speed_kmh": (0.0, 25.0),
    "heading_deg": (0.0, 360.0),
    "fuel_pct": (0.0, 100.0),
}

ALLOWED_COMMANDS = {
    "engine_start": [
        "decompression_engage",
        "crank_start",
        "crank_stop",
        "decompression_release",
    ],
    "engine_stop": [],
    "cooling_on": [],
    "cooling_off": [],
    "emergency_stop": ["fuel_cutoff", "crank_stop", "cooling_off"],
}


def now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def get_users_list():
    snapshot = db.reference("/users").get()
    if not snapshot:
        return []
    users = []
    if isinstance(snapshot, dict):
        for k, v in snapshot.items():
            if isinstance(v, dict):
                u = dict(v)
                u["id"] = v.get("id", k)
                users.append(u)
    elif isinstance(snapshot, list):
        for idx, v in enumerate(snapshot):
            if isinstance(v, dict):
                u = dict(v)
                u["id"] = v.get("id", idx)
                users.append(u)
    return users


def is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
    )


def authorized():
    if session.get("role") == "admin":
        return True
    provided = request.headers.get("X-API-Key", "")
    try:
        valid = secrets.compare_digest(provided, API_KEY)
    except TypeError:
        valid = False
    if not valid:
        print(
            f"[SUSPICIOUS] unauthorized dari {request.remote_addr} ke {request.path}",
            flush=True,
        )
    return valid


def reject(reason, payload=None):
    print(f"[SUSPICIOUS] {reason} dari {request.remote_addr}: {payload}", flush=True)
    return jsonify({"error": reason}), 400


def thermal_state(engine_temp_c):
    if engine_temp_c >= 105.0:
        return "critical", True
    if engine_temp_c >= 95.0:
        return "warning", False
    return "normal", False


def haversine_m(start, end):
    lat1, lon1 = radians(start[0]), radians(start[1])
    lat2, lon2 = radians(end[0]), radians(end[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371000 * asin(sqrt(min(1.0, h)))


def latest_from_ref(path):
    snapshot = db.reference(path).order_by_key().limit_to_last(1).get()
    if not snapshot or not isinstance(snapshot, dict):
        return None
    for key, val in snapshot.items():
        if isinstance(val, dict):
            item = dict(val)
            item["id"] = key
            return item
    return None


def read_history(limit):
    snapshot = db.reference("/telemetry").order_by_key().limit_to_last(limit).get()
    if not snapshot or not isinstance(snapshot, dict):
        return []
    items = []
    for key, val in snapshot.items():
        if isinstance(val, dict):
            row = dict(val)
            row["id"] = key
            row["cooling_active"] = bool(row.get("cooling_active", False))
            items.append(row)
    items.reverse()
    return items


def read_status():
    telemetry = latest_from_ref("/telemetry")
    if telemetry:
        telemetry["cooling_active"] = bool(telemetry.get("cooling_active", False))
    command = latest_from_ref("/commands")
    route = latest_from_ref("/routes")
    return {
        "device": "GeoSync",
        "telemetry": telemetry,
        "last_command": command,
        "route": route,
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user_id" in session:
            return redirect(url_for("dashboard"))
        return render_template("login.html", error=None)

    payload = request.get_json(silent=True) if request.is_json else request.form
    username = str((payload or {}).get("username", "")).strip()
    password = str((payload or {}).get("password", "")).strip()

    if not username or not password:
        if request.is_json:
            return jsonify({"error": "Username dan password wajib diisi"}), 400
        return render_template("login.html", error="Username dan password wajib diisi."), 400

    matched_user = None
    try:
        snapshot = db.reference("/users").get()
        if snapshot:
            user_items = snapshot.items() if isinstance(snapshot, dict) else enumerate(snapshot)
            for k, v in user_items:
                if (
                    isinstance(v, dict)
                    and str(v.get("username", "")).strip() == username
                    and str(v.get("password", "")).strip() == password
                ):
                    matched_user = dict(v)
                    matched_user["id"] = v.get("id", k)
                    break
    except Exception as exc:
        print(f"[AUTH-ERROR] Gagal query user ke Firebase: {exc}", flush=True)
        if request.is_json:
            return jsonify({"error": "Gagal terhubung ke database autentikasi"}), 500
        return render_template("login.html", error="Koneksi database bermasalah."), 500

    if not matched_user:
        print(
            f"[AUTH-FAIL] login gagal dari {request.remote_addr} untuk user={username!r}",
            flush=True,
        )
        if request.is_json:
            return jsonify({"error": "Username atau password salah"}), 401
        return render_template("login.html", error="Username atau password salah."), 401

    session["user_id"] = matched_user["id"]
    session["username"] = matched_user["username"]
    session["role"] = matched_user.get("role", "user")
    session["full_name"] = matched_user.get("full_name", matched_user["username"])

    print(
        f"[AUTH-OK] login berhasil dari {request.remote_addr} -> "
        f"user={session['username']} (role={session['role']})",
        flush=True,
    )

    if request.is_json:
        return (
            jsonify(
                {
                    "status": "ok",
                    "username": session["username"],
                    "role": session["role"],
                    "full_name": session["full_name"],
                }
            ),
            200,
        )

    return redirect(url_for("dashboard"))


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template(
        "dashboard.html",
        user={
            "username": session.get("username"),
            "role": session.get("role"),
            "full_name": session.get("full_name"),
        },
    )


@app.route("/api/telemetry", methods=["POST"])
def receive_telemetry():
    if not authorized():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return reject("payload tidak valid", data)

    for field, (minimum, maximum) in TELEMETRY_RULES.items():
        if field not in data:
            return reject("payload tidak valid", data)
        value = data[field]
        if not is_number(value) or not (minimum <= value <= maximum):
            return reject(f"nilai {field} tidak valid", data)

    engine_temp_c = float(data["engine_temp_c"])
    thermal_status, cooling_active = thermal_state(engine_temp_c)

    if thermal_status == "critical":
        print(
            f"[THERMAL] suhu mesin {engine_temp_c}C, cooling diaktifkan otomatis",
            flush=True,
        )
    elif thermal_status == "warning":
        print(f"[THERMAL] suhu mesin {engine_temp_c}C, mendekati batas", flush=True)

    record = {
        "engine_temp_c": engine_temp_c,
        "rpm": float(data["rpm"]),
        "latitude": float(data["latitude"]),
        "longitude": float(data["longitude"]),
        "speed_kmh": float(data["speed_kmh"]),
        "heading_deg": float(data["heading_deg"]),
        "fuel_pct": float(data["fuel_pct"]),
        "thermal_status": thermal_status,
        "cooling_active": cooling_active,
        "ts": now_ts(),
    }

    new_ref = db.reference("/telemetry").push(record)

    return (
        jsonify(
            {
                "status": "ok",
                "id": new_ref.key,
                "thermal_status": thermal_status,
                "cooling_active": cooling_active,
            }
        ),
        201,
    )


@app.route("/api/telemetry/history", methods=["GET"])
def telemetry_history():
    if not authorized():
        return jsonify({"error": "unauthorized"}), 401

    raw_limit = request.args.get("limit", "20")
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return reject("limit tidak valid", raw_limit)

    if not 1 <= limit <= 100:
        return reject("limit tidak valid", raw_limit)

    rows = read_history(limit)
    return jsonify({"count": len(rows), "data": rows}), 200


@app.route("/api/command", methods=["POST"])
def queue_command():
    if not authorized():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("command"), str):
        return reject("payload tidak valid", data)

    command = data["command"].strip()
    if command not in ALLOWED_COMMANDS:
        return reject("perintah tidak dikenal", data)

    actor = session.get("username", "api-key")
    record = {
        "command": command,
        "issued_by": actor,
        "status": "accepted",
        "ts": now_ts(),
    }
    new_ref = db.reference("/commands").push(record)

    payload = {
        "status": "accepted",
        "id": new_ref.key,
        "command": command,
        "issued_by": actor,
    }
    if ALLOWED_COMMANDS[command]:
        payload["sequence"] = ALLOWED_COMMANDS[command]
    return jsonify(payload), 202


@app.route("/api/route", methods=["POST"])
def create_route():
    if not authorized():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return reject("payload tidak valid", data)

    name = data.get("name", "rute-geosync")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        return reject("nama rute tidak valid", data)

    waypoints = data.get("waypoints")
    if not isinstance(waypoints, list) or not 2 <= len(waypoints) <= 100:
        return reject("waypoints tidak valid", data)

    cleaned = []
    for point in waypoints:
        if not isinstance(point, list) or len(point) != 2:
            return reject("waypoints tidak valid", data)
        latitude, longitude = point
        if (
            not is_number(latitude)
            or not is_number(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            return reject("koordinat tidak valid", data)
        cleaned.append([float(latitude), float(longitude)])

    distance_m = sum(
        haversine_m(cleaned[index], cleaned[index + 1])
        for index in range(len(cleaned) - 1)
    )

    record = {
        "name": name.strip(),
        "waypoints": cleaned,
        "distance_m": round(distance_m, 2),
        "ts": now_ts(),
    }
    new_ref = db.reference("/routes").push(record)

    return (
        jsonify(
            {
                "status": "ok",
                "route_id": new_ref.key,
                "name": name.strip(),
                "waypoints": len(cleaned),
                "distance_m": round(distance_m, 2),
            }
        ),
        201,
    )


@app.route("/api/users", methods=["GET"])
def api_users():
    if not authorized():
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"users": get_users_list()}), 200


@app.route("/api/status", methods=["GET"])
def device_status():
    if not authorized():
        return jsonify({"error": "unauthorized"}), 401

    return jsonify(read_status()), 200


@app.route("/dashboard/data", methods=["GET"])
def dashboard_data():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    payload = read_status()
    payload["history"] = read_history(10)
    payload["current_user"] = {
        "username": session.get("username"),
        "role": session.get("role"),
        "full_name": session.get("full_name"),
    }
    if session.get("role") == "admin":
        payload["users"] = get_users_list()
    return jsonify(payload), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
