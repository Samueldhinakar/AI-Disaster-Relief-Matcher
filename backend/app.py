from flask import Flask, request, jsonify, send_from_directory
import os
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)
FRONTEND_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
    "dist"
)

@app.route("/")
def serve_frontend():
    return send_from_directory(FRONTEND_FOLDER, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    file_path = os.path.join(FRONTEND_FOLDER, path)

    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_FOLDER, path)

    return send_from_directory(FRONTEND_FOLDER, "index.html")

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disaster_relief.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            urgency TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            provider TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            urgency TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            team TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            created_at TEXT NOT NULL
        )
    """)

    # Stores every confirmed AI match.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS match_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            resource_name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            requested_quantity REAL NOT NULL,
            supplied_quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            urgency TEXT NOT NULL,
            location TEXT NOT NULL,
            donor TEXT NOT NULL,
            rescue_team TEXT NOT NULL,
            ai_score REAL NOT NULL,
            matched_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def row_to_dict(row):
    return dict(row)

def urgency_score(value):
    return {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1
    }.get(value, 1)

def calculate_match(resource, req):
    score = 0

    if resource["type"].lower() == req["type"].lower():
        score += 35

    if resource["name"].lower() == req["name"].lower():
        score += 20

    if resource["quantity"] >= req["quantity"]:
        score += 25
    else:
        score += 25 * (resource["quantity"] / req["quantity"])

    score += urgency_score(req["urgency"]) * 4

    if (
        resource["latitude"] is not None
        and resource["longitude"] is not None
        and req["latitude"] is not None
        and req["longitude"] is not None
    ):
        lat_diff = abs(resource["latitude"] - req["latitude"])
        lon_diff = abs(resource["longitude"] - req["longitude"])
        distance_factor = max(0, 12 - (lat_diff + lon_diff) * 20)
        score += distance_factor
    elif resource["location"].lower() == req["location"].lower():
        score += 10

    return round(min(score, 100), 2)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/resources", methods=["GET", "POST"])
def resources():
    conn = get_db()

    if request.method == "POST":
        data = request.get_json() or {}

        required = [
            "type", "name", "quantity", "unit",
            "urgency", "location", "provider"
        ]

        missing = [x for x in required if not data.get(x)]

        if missing:
            conn.close()
            return jsonify({
                "error": "Missing fields",
                "fields": missing
            }), 400

        conn.execute("""
            INSERT INTO resources
            (type, name, quantity, unit, urgency, location,
             latitude, longitude, provider, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available', ?)
        """, (
            data["type"],
            data["name"],
            float(data["quantity"]),
            data["unit"],
            data["urgency"],
            data["location"],
            data.get("latitude"),
            data.get("longitude"),
            data["provider"],
            datetime.now().isoformat(timespec="seconds")
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Resource posted successfully"
        }), 201

    rows = conn.execute("""
        SELECT * FROM resources
        WHERE status='Available'
        ORDER BY id DESC
    """).fetchall()

    conn.close()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/requests", methods=["GET", "POST"])
def requests_api():
    conn = get_db()

    if request.method == "POST":
        data = request.get_json() or {}

        required = [
            "type", "name", "quantity", "unit",
            "urgency", "location", "team"
        ]

        missing = [x for x in required if not data.get(x)]

        if missing:
            conn.close()
            return jsonify({
                "error": "Missing fields",
                "fields": missing
            }), 400

        conn.execute("""
            INSERT INTO requests
            (type, name, quantity, unit, urgency, location,
             latitude, longitude, team, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Open', ?)
        """, (
            data["type"],
            data["name"],
            float(data["quantity"]),
            data["unit"],
            data["urgency"],
            data["location"],
            data.get("latitude"),
            data.get("longitude"),
            data["team"],
            datetime.now().isoformat(timespec="seconds")
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Request posted successfully"
        }), 201

    rows = conn.execute("""
        SELECT * FROM requests
        WHERE status='Open'
        ORDER BY id DESC
    """).fetchall()

    conn.close()
    return jsonify([row_to_dict(r) for r in rows])
@app.route("/api/requests/all")
def all_requests():
    conn = get_db()

    rows = conn.execute("""
        SELECT * FROM requests
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([row_to_dict(r) for r in rows])
def get_matches():
    conn = get_db()

    resources = conn.execute("""
        SELECT * FROM resources
        WHERE status='Available' AND quantity > 0
    """).fetchall()

    requests = conn.execute("""
        SELECT * FROM requests
        WHERE status='Open'
    """).fetchall()

    conn.close()

    matches = []

    for req in requests:
        candidates = []

        for resource in resources:

            # Match resource category/type
            if resource["type"].lower() != req["type"].lower():
                continue

            # Match product name
            if resource["name"].lower() != req["name"].lower():
                continue

            score = calculate_match(resource, req)

            candidates.append({
                "request": row_to_dict(req),
                "resource": row_to_dict(resource),
                "score": score,
                "quantity_match": min(
                    float(resource["quantity"]),
                    float(req["quantity"])
                ),
                "reason": (
                    "Matched using resource type, product name, "
                    "quantity, urgency and location."
                )
            })

        # Highest scoring donor first
        candidates.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        # Add ALL suitable donors
        if candidates:
            matches.extend(candidates)

    # Sort by urgency first, then AI score
    matches.sort(
        key=lambda x: (
            urgency_score(x["request"]["urgency"]),
            x["score"]
        ),
        reverse=True
    )

    return matches

@app.route("/api/matches")
def matches():
    return jsonify(get_matches())

@app.route("/api/matches/run", methods=["POST"])
def run_matching():
    return jsonify(get_matches())

@app.route("/api/matches/<int:request_id>/confirm", methods=["POST"])
def confirm_match(request_id):
    data = request.get_json() or {}
    resource_id = data.get("resource_id")
    ai_score = float(data.get("ai_score", 0))

    if not resource_id:
        return jsonify({"error": "resource_id is required"}), 400

    conn = get_db()

    # Get the rescue request
    req = conn.execute(
        "SELECT * FROM requests WHERE id=?",
        (request_id,)
    ).fetchone()

    # Get the donor resource
    resource = conn.execute(
        "SELECT * FROM resources WHERE id=?",
        (resource_id,)
    ).fetchone()

    if not req or not resource:
        conn.close()
        return jsonify({
            "error": "Request or resource not found"
        }), 404

    # Allow Open requests to receive multiple donors
    if req["status"] == "Matched":
        conn.close()
        return jsonify({
            "error": "This request has already been completely fulfilled."
        }), 400

    available = float(resource["quantity"])
    requested_quantity = float(req["quantity"])

    if available <= 0:
        conn.close()
        return jsonify({
            "error": "Resource is no longer available."
        }), 400

    # -------------------------------------------------
    # Calculate how much has already been supplied
    # -------------------------------------------------

    fulfilled_row = conn.execute("""
        SELECT COALESCE(SUM(supplied_quantity), 0) AS total_supplied
        FROM match_history
        WHERE request_id=?
    """, (request_id,)).fetchone()

    already_supplied = float(fulfilled_row["total_supplied"])

    remaining_needed = requested_quantity - already_supplied

    if remaining_needed <= 0:
        conn.execute(
            "UPDATE requests SET status='Matched' WHERE id=?",
            (request_id,)
        )
        conn.commit()
        conn.close()

        return jsonify({
            "message": "This request has already been completely fulfilled."
        }), 400

    # -------------------------------------------------
    # Calculate this donor's contribution
    # -------------------------------------------------

    supplied = min(remaining_needed, available)

    remaining_resource = available - supplied
    remaining_request = remaining_needed - supplied

    # -------------------------------------------------
    # Save this donor match in history
    # -------------------------------------------------

    conn.execute("""
        INSERT INTO match_history
        (request_id, resource_id, resource_name, resource_type,
         requested_quantity, supplied_quantity, unit, urgency,
         location, donor, rescue_team, ai_score, matched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req["id"],
        resource["id"],
        resource["name"],
        resource["type"],
        requested_quantity,
        supplied,
        resource["unit"],
        req["urgency"],
        req["location"],
        resource["provider"],
        req["team"],
        ai_score,
        datetime.now().isoformat(timespec="seconds")
    ))

    # -------------------------------------------------
    # Update donor inventory
    # -------------------------------------------------

    if remaining_resource <= 0:
        conn.execute("""
            UPDATE resources
            SET quantity=0, status='Matched'
            WHERE id=?
        """, (resource_id,))
    else:
        conn.execute("""
            UPDATE resources
            SET quantity=?
            WHERE id=?
        """, (remaining_resource, resource_id))

    # -------------------------------------------------
    # Update request status
    # -------------------------------------------------

    if remaining_request <= 0:
        # Entire request has been fulfilled
        conn.execute("""
            UPDATE requests
            SET status='Matched'
            WHERE id=?
        """, (request_id,))

        final_status = "Matched"
    else:
        # More donors are still required
        # Keep request Open so another donor can fulfill it
        conn.execute("""
            UPDATE requests
            SET status='Open'
            WHERE id=?
        """, (request_id,))

        final_status = "Partially Matched"

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Donor contribution confirmed successfully.",
        "supplied_quantity": supplied,
        "remaining_request_quantity": remaining_request,
        "remaining_resource_quantity": remaining_resource,
        "request_status": final_status
    })
@app.route("/api/inventory")
def inventory():
    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM resources
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([row_to_dict(r) for r in rows])




@app.route("/api/requests/<int:request_id>/status", methods=["PUT"])
def update_request_status(request_id):
    data = request.get_json() or {}
    new_status = data.get("status")

    allowed_statuses = [
        "Open",
        "Matched",
        "In Transit",
        "Delivered"
    ]

    if new_status not in allowed_statuses:
        return jsonify({
            "error": "Invalid status",
            "allowed_statuses": allowed_statuses
        }), 400

    conn = get_db()

    request_row = conn.execute(
        "SELECT * FROM requests WHERE id=?",
        (request_id,)
    ).fetchone()

    if not request_row:
        conn.close()
        return jsonify({
            "error": "Request not found"
        }), 404

    conn.execute(
        "UPDATE requests SET status=? WHERE id=?",
        (new_status, request_id)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Request status updated successfully",
        "request_id": request_id,
        "status": new_status
    })
@app.route("/api/history")
def history():
    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM match_history
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/reset", methods=["POST"])
def reset():
    conn = get_db()

    conn.execute("DELETE FROM resources")
    conn.execute("DELETE FROM requests")
    conn.execute("DELETE FROM match_history")

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Demo data and match history cleared."
    })

init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
