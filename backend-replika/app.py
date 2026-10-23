import json
import os
import secrets
import sqlite3
from math import asin, cos, isfinite, radians, sin, sqrt

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")

load_dotenv(os.path.join(BASE_DIR, ".env"))
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise RuntimeError("API_KEY belum diset. Isi file .env (contoh ada di .env.example).")

app = Flask(__name__)
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


def is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
    )


def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                engine_temp_c REAL NOT NULL,
                rpm REAL NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                speed_kmh REAL NOT NULL,
                heading_deg REAL NOT NULL,
                fuel_pct REAL NOT NULL,
                thermal_status TEXT NOT NULL,
                cooling_active INTEGER NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'accepted',
                ts TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                waypoints TEXT NOT NULL,
                distance_m REAL NOT NULL,
                ts TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def authorized():
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
        return "critical", 1
    if engine_temp_c >= 95.0:
        return "warning", 0
    return "normal", 0


def telemetry_to_dict(row):
    item = dict(row)
    item["cooling_active"] = bool(item["cooling_active"])
    return item


def haversine_m(start, end):
    lat1, lon1 = radians(start[0]), radians(start[1])
    lat2, lon2 = radians(end[0]), radians(end[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371000 * asin(sqrt(min(1.0, h)))


@app.route("/", methods=["GET"])
def dashboard():
    return render_template("dashboard.html")


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

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO telemetry (
                engine_temp_c, rpm, latitude, longitude,
                speed_kmh, heading_deg, fuel_pct, thermal_status, cooling_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                engine_temp_c,
                float(data["rpm"]),
                float(data["latitude"]),
                float(data["longitude"]),
                float(data["speed_kmh"]),
                float(data["heading_deg"]),
                float(data["fuel_pct"]),
                thermal_status,
                cooling_active,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return (
        jsonify(
            {
                "status": "ok",
                "thermal_status": thermal_status,
                "cooling_active": bool(cooling_active),
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

    conn = get_db()
    try:
        conn.execute("INSERT INTO commands (command) VALUES (?)", (command,))
        conn.commit()
    finally:
        conn.close()

    payload = {"status": "accepted", "command": command}
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
        cleaned.append((float(latitude), float(longitude)))

    distance_m = sum(
        haversine_m(cleaned[index], cleaned[index + 1])
        for index in range(len(cleaned) - 1)
    )

    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO routes (name, waypoints, distance_m) VALUES (?, ?, ?)",
            (name.strip(), json.dumps(cleaned), round(distance_m, 2)),
        )
        conn.commit()
        route_id = cursor.lastrowid
    finally:
        conn.close()

    return (
        jsonify(
            {
                "status": "ok",
                "route_id": route_id,
                "name": name.strip(),
                "waypoints": len(cleaned),
                "distance_m": round(distance_m, 2),
            }
        ),
        201,
    )


def read_status():
    conn = get_db()
    try:
        telemetry = conn.execute(
            "SELECT * FROM telemetry ORDER BY id DESC LIMIT 1"
        ).fetchone()
        command = conn.execute(
            "SELECT command, status, ts FROM commands ORDER BY id DESC LIMIT 1"
        ).fetchone()
        route = conn.execute(
            "SELECT id, name, waypoints, distance_m, ts FROM routes "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    payload = {
        "device": "GeoSync",
        "telemetry": telemetry_to_dict(telemetry) if telemetry else None,
        "last_command": dict(command) if command else None,
        "route": None,
    }

    if route:
        route_data = dict(route)
        route_data["waypoints"] = json.loads(route_data["waypoints"])
        payload["route"] = route_data

    return payload


def read_history(limit):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    finally:
        conn.close()
    return [telemetry_to_dict(row) for row in rows]


@app.route("/api/status", methods=["GET"])
def device_status():
    if not authorized():
        return jsonify({"error": "unauthorized"}), 401

    return jsonify(read_status()), 200


@app.route("/dashboard/data", methods=["GET"])
def dashboard_data():
    payload = read_status()
    payload["history"] = read_history(10)
    return jsonify(payload), 200


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
