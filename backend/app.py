import re
from flask import Flask, request, jsonify, send_from_directory
import os
from flask_cors import CORS
import sqlite3
from datetime import datetime
import requests
import csv
import math

app = Flask(__name__)
CORS(app)
FRONTEND_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
    "dist"
)
DISTRICT_COORDINATES = {

    "ARIYALUR": (11.1401, 79.0786),
    "CHENGALPATTU": (12.6819, 79.9888),
    "CHENNAI": (13.0827, 80.2707),
    "COIMBATORE": (11.0168, 76.9558),
    "CUDDALORE": (11.7480, 79.7714),
    "DHARMAPURI": (12.1211, 78.1582),
    "DINDIGUL": (10.3673, 77.9803),
    "ERODE": (11.3410, 77.7172),
    "KALLAKURICHI": (11.7401, 78.9597),
    "KANCHIPURAM": (12.8342, 79.7036),
    "KANNIYAKUMARI": (8.0883, 77.5385),
    "KARUR": (10.9601, 78.0766),
    "KRISHNAGIRI": (12.5186, 78.2137),
    "MADURAI": (9.9252, 78.1198),
    "MAYILADUTHURAI": (11.1018, 79.6525),
    "NAGAPATTINAM": (10.7656, 79.8424),
    "NAMAKKAL": (11.2194, 78.1677),
    "PERAMBALUR": (11.2342, 78.8806),
    "PUDUKKOTTAI": (10.3797, 78.8208),
    "RAMANATHAPURAM": (9.3639, 78.8395),
    "RANIPET": (12.9249, 79.3333),
    "SALEM": (11.6643, 78.1460),
    "SIVAGANGA": (9.8433, 78.4809),
    "TENKASI": (8.9591, 77.3152),
    "THANJAVUR": (10.7870, 79.1378),
    "THE NILGIRIS": (11.4102, 76.6950),
    "THENI": (10.0104, 77.4768),
    "THOOTHUKUDI": (8.7642, 78.1348),
    "TIRUCHIRAPPALLI": (10.7905, 78.7047),
    "TIRUNELVELI": (8.7139, 77.7567),
    "TIRUPATHUR": (12.4970, 78.5670),
    "TIRUPPUR": (11.1085, 77.3411),
    "TIRUVALLUR": (13.1438, 79.9080),
    "TIRUVANNAMALAI": (12.2253, 79.0747),
    "TIRUVARUR": (10.7725, 79.6368),
    "VELLORE": (12.9165, 79.1325),
    "VILLUPURAM": (11.9401, 79.4861),
    "VIRUDHUNAGAR": (9.5680, 77.9624)
}
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
# CWC CSV file
CWC_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "rwl_tel_hr_cwc_009_2026_2030.csv"
)

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
# =========================================================
# PRE-DISASTER AI RISK ENGINE
# =========================================================

IMD_WARNING_SCORES = {
    1: 0,
    2: 55,
    3: 20,
    4: 35,
    5: 30,
    6: 10,
    7: 10,
    8: 20,
    9: 10,
    10: 10,
    11: 10,
    12: 20,
    13: 20,
    14: 10,
    15: 10,
    16: 75,
    17: 95
}


IMD_COLOR_SCORES = {
    1: 95,
    2: 70,
    3: 35,
    4: 10
}


CWC_FLOOD_SCORES = {
    "Normal": 10,
    "Above Normal": 55,
    "Severe": 80,
    "Extreme": 100
}


CWC_TREND_ADJUSTMENT = {
    "Rising": 10,
    "Steady": 0,
    "Falling": -5
}


def calculate_pre_disaster_risk(
    imd_warning_score,
    imd_color_score,
    cwc_flood_score,
    cwc_trend
):

    # Select the more severe IMD indicator
    imd_score = max(
        imd_warning_score,
        imd_color_score
    )

    # Adjust CWC score based on river trend
    trend_adjustment = CWC_TREND_ADJUSTMENT.get(
        cwc_trend,
        0
    )

    cwc_score = cwc_flood_score + trend_adjustment

    # Keep score between 0 and 100
    cwc_score = max(
        0,
        min(100, cwc_score)
    )

    # Calculate final AI risk score
    final_score = (
        (imd_score * 0.60) +
        (cwc_score * 0.40)
    )

    final_score = round(
        max(0, min(100, final_score))
    )

    # Determine risk level
    if final_score >= 75:
        risk_level = "CRITICAL"

    elif final_score >= 50:
        risk_level = "HIGH"

    elif final_score >= 25:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    return {
        "imd_score": round(imd_score),
        "cwc_score": round(cwc_score),
        "final_score": final_score,
        "risk_level": risk_level,
        "trend_adjustment": trend_adjustment
    }
def test_cwc_file():

    if os.path.exists(CWC_FILE):
        return {
            "status": "success",
            "message": "CWC CSV file found",
            "file": CWC_FILE
        }

    return {
        "status": "error",
        "message": "CWC CSV file not found",
        "file": CWC_FILE
    }
def read_cwc_data():

    if not os.path.exists(CWC_FILE):
        raise FileNotFoundError("CWC CSV file not found.")

    records = []

    with open(
        CWC_FILE,
        "r",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:
                record = {
                    "station": row["Station"],
                    "state": row["State"],
                    "district": row["District"],
                    "tehsil": row["Tehsil"],
                    "river": row["River"],
                    "basin": row["Basin"],
                    "latitude": float(row["Latitude"]),
                    "longitude": float(row["Longitude"]),
                    "water_level": float(
                        row[
                            "River Water Level Telemetry Hourly (meter)"
                        ]
                    ),
                    "time": row["Data Acquisition Time"]
                }

                records.append(record)

            except (ValueError, KeyError, TypeError):
                continue

    return records
def calculate_distance(lat1, lon1, lat2, lon2):

    radius = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radius * c
def find_nearest_cwc_station(latitude, longitude):

    records = read_cwc_data()

    if not records:
        raise ValueError("No CWC records available.")

    latitude = float(latitude)
    longitude = float(longitude)

    stations = {}

    # Keep only one location for each station
    for record in records:

        station = record["station"]

        if station not in stations:

            stations[station] = {
                "station": record["station"],
                "state": record["state"],
                "district": record["district"],
                "tehsil": record["tehsil"],
                "river": record["river"],
                "basin": record["basin"],
                "latitude": record["latitude"],
                "longitude": record["longitude"]
            }

    nearest_station = None
    nearest_distance = float("inf")

    for station in stations.values():

        distance = calculate_distance(
            latitude,
            longitude,
            station["latitude"],
            station["longitude"]
        )

        if distance < nearest_distance:

            nearest_distance = distance
            nearest_station = station

    if nearest_station is None:
        raise ValueError("No nearby CWC station found.")

    nearest_station["distance_km"] = round(
        nearest_distance,
        2
    )

    return nearest_station
def get_latest_cwc_reading(latitude, longitude):

    records = read_cwc_data()

    if not records:
        raise ValueError("No CWC records available.")

    nearest_station = find_nearest_cwc_station(
        latitude,
        longitude
    )

    station_name = nearest_station["station"]

    station_records = [
        record
        for record in records
        if record["station"] == station_name
    ]

    if not station_records:
        raise ValueError(
            "No readings found for nearest CWC station."
        )

    # Sort readings by date and time
    station_records.sort(
        key=lambda record: datetime.strptime(
            record["time"],
            "%d-%m-%Y %H:%M"
        )
    )

    latest = station_records[-1]

    return {
        "station": nearest_station["station"],
        "district": nearest_station["district"],
        "state": nearest_station["state"],
        "river": nearest_station["river"],
        "basin": nearest_station["basin"],
        "tehsil": nearest_station["tehsil"],
        "latitude": nearest_station["latitude"],
        "longitude": nearest_station["longitude"],
        "distance_km": nearest_station["distance_km"],
        "latest_time": latest["time"],
        "water_level": latest["water_level"]
    }
def get_cwc_trend(latitude, longitude):

    records = read_cwc_data()

    if not records:
        raise ValueError("No CWC records available.")

    nearest_station = find_nearest_cwc_station(
        latitude,
        longitude
    )

    station_name = nearest_station["station"]

    station_records = [
        record
        for record in records
        if record["station"] == station_name
    ]

    if len(station_records) < 2:
        raise ValueError(
            "Not enough readings for this CWC station."
        )

    # Convert time strings into datetime objects
    for record in station_records:

        record["datetime"] = datetime.strptime(
            record["time"],
            "%d-%m-%Y %H:%M"
        )

    # Sort oldest → newest
    station_records.sort(
        key=lambda record: record["datetime"]
    )

    latest = station_records[-1]

    # Only examine readings from the recent 24-hour period
    recent_records = [
        record
        for record in station_records
        if (
            latest["datetime"] - record["datetime"]
        ).total_seconds() <= 24 * 60 * 60
    ]

    # Remove suspicious sudden jumps
    valid_records = []

    for record in recent_records:

        if not valid_records:

            valid_records.append(record)
            continue

        previous = valid_records[-1]

        difference = abs(
            record["water_level"]
            - previous["water_level"]
        )

        if difference <= 5:

            valid_records.append(record)

    # We need at least two recent valid readings
    if len(valid_records) < 2:

        return {
            "station": station_name,
            "latest_time": latest["time"],
            "latest_water_level": latest["water_level"],
            "trend": "Insufficient recent data",
            "difference": None,
            "previous_time": None,
            "previous_water_level": None,
            "data_quality_note": (
                "There are not enough valid readings "
                "within the last 24 hours to calculate "
                "a reliable trend."
            )
        }

    latest_valid = valid_records[-1]
    previous_valid = valid_records[-2]

    latest_level = latest_valid["water_level"]
    previous_level = previous_valid["water_level"]

    difference = latest_level - previous_level

    if difference > 0.01:

        trend = "Rising"

    elif difference < -0.01:

        trend = "Falling"

    else:

        trend = "Steady"

    return {
        "station": station_name,
        "latest_time": latest_valid["time"],
        "latest_water_level": latest_level,
        "previous_time": previous_valid["time"],
        "previous_water_level": previous_level,
        "difference": round(difference, 3),
        "trend": trend,
        "data_quality_note": (
            "Trend calculated using valid readings "
            "from the last 24 hours."
        )
    }
# =========================================================
# CWC HISTORICAL BASELINE
# =========================================================

# =========================================================
# CWC HISTORICAL BASELINE - CLEAN VERSION
# =========================================================

def get_cwc_station_baseline(latitude, longitude):

    station = find_nearest_cwc_station(latitude, longitude)

    if not station:
        return {
            "status": "error",
            "message": "No nearby CWC station found"
        }

    station_name = station["station"]

    records = read_cwc_data()

    station_records = [
        r for r in records
        if r["station"] == station_name
    ]

    if not station_records:
        return {
            "status": "error",
            "message": "No water-level data found for this station"
        }

    # -----------------------------------------------------
    # Convert water levels to valid numbers
    # -----------------------------------------------------

    valid_records = []

    for record in station_records:

        try:
            value = float(record["water_level"])

            # Ignore NaN and infinity
            if math.isnan(value) or math.isinf(value):
                continue

            valid_records.append({
                **record,
                "numeric_level": value
            })

        except (ValueError, TypeError):
            continue

    if not valid_records:
        return {
            "status": "error",
            "message": "No valid water-level values found"
        }

    # -----------------------------------------------------
    # Sort records by time
    # -----------------------------------------------------

    valid_records.sort(
        key=lambda r: datetime.strptime(
            r["time"],
            "%d-%m-%Y %H:%M"
        )
    )

    # -----------------------------------------------------
    # Remove obvious abnormal jumps
    #
    # This is a DATA QUALITY filter.
    # It is NOT a flood threshold.
    # -----------------------------------------------------

    clean_records = []

    previous_level = None

    for record in valid_records:

        level = record["numeric_level"]

        if previous_level is not None:

            difference = abs(
                level - previous_level
            )

            # Ignore extremely large sudden jumps
            if difference > 5:
                continue

        clean_records.append(record)

        previous_level = level

    if not clean_records:
        return {
            "status": "error",
            "message": "No clean CWC readings available"
        }

    # -----------------------------------------------------
    # Extract clean water levels
    # -----------------------------------------------------

    water_levels = [
        r["numeric_level"]
        for r in clean_records
    ]

    water_levels.sort()

    # -----------------------------------------------------
    # Basic statistics
    # -----------------------------------------------------

    minimum = min(water_levels)
    maximum = max(water_levels)

    average = (
        sum(water_levels) /
        len(water_levels)
    )

    # -----------------------------------------------------
    # Percentile function
    # -----------------------------------------------------

    def percentile(values, percentage):

        index = (
            (len(values) - 1)
            * percentage
        )

        lower = int(index)

        upper = min(
            lower + 1,
            len(values) - 1
        )

        weight = index - lower

        return (
            values[lower]
            +
            (
                values[upper]
                -
                values[lower]
            )
            * weight
        )

    percentile_90 = percentile(
        water_levels,
        0.90
    )

    percentile_95 = percentile(
        water_levels,
        0.95
    )

    # -----------------------------------------------------
    # Latest clean reading
    # -----------------------------------------------------

    latest_record = max(
        clean_records,
        key=lambda r: datetime.strptime(
            r["time"],
            "%d-%m-%Y %H:%M"
        )
    )

    latest_level = latest_record[
        "numeric_level"
    ]

    return {

        "status": "success",

        "station": station_name,

        "river": station["river"],

        "district": station["district"],

        "state": station["state"],

        "distance_km": station[
            "distance_km"
        ],

        "total_readings": len(
            water_levels
        ),

        "minimum_level": round(
            minimum,
            3
        ),

        "maximum_level": round(
            maximum,
            3
        ),

        "average_level": round(
            average,
            3
        ),

        "percentile_90": round(
            percentile_90,
            3
        ),

        "percentile_95": round(
            percentile_95,
            3
        ),

        "latest_level": round(
            latest_level,
            3
        ),

        "latest_time": latest_record[
            "time"
        ]
    }
def calculate_cwc_historical_score(latitude, longitude):

    baseline = get_cwc_station_baseline(
        latitude,
        longitude
    )

    if baseline.get("status") != "success":
        return baseline

    latest = baseline["latest_level"]
    p90 = baseline["percentile_90"]
    p95 = baseline["percentile_95"]
    minimum = baseline["minimum_level"]

    # Historical water-level score
    if latest <= minimum:
        score = 10

    elif latest <= p90:

        # Scale between minimum and 90th percentile
        score = 10 + (
            (latest - minimum)
            /
            (p90 - minimum)
        ) * 60

    elif latest <= p95:

        # 90th to 95th percentile
        score = 70 + (
            (latest - p90)
            /
            (p95 - p90)
        ) * 15

    else:

        # Above 95th percentile
        score = 85

        if latest > p95:
            extra = (
                (latest - p95)
                /
                max(p95 - minimum, 0.001)
            ) * 15

            score += extra

    score = round(
        max(0, min(100, score))
    )

    if score >= 85:
        level = "VERY HIGH"
    elif score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "status": "success",

        "station": baseline["station"],
        "river": baseline["river"],
        "district": baseline["district"],
        "state": baseline["state"],

        "latest_level": baseline["latest_level"],
        "latest_time": baseline["latest_time"],

        "minimum_level": baseline["minimum_level"],
        "average_level": baseline["average_level"],
        "percentile_90": baseline["percentile_90"],
        "percentile_95": baseline["percentile_95"],

        "cwc_score": score,
        "cwc_level": level,

        "explanation":
            "Score is based on the latest water level "
            "compared with the station's historical "
            "water-level distribution."
    }
def calculate_final_pre_disaster_risk(
    imd_score,
    cwc_score
):

    final_score = (
        (imd_score * 0.60)
        +
        (cwc_score * 0.40)
    )

    final_score = round(
        max(0, min(100, final_score))
    )

    if final_score >= 75:
        risk_level = "CRITICAL"

    elif final_score >= 50:
        risk_level = "HIGH"

    elif final_score >= 25:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    return {
        "final_score": final_score,
        "risk_level": risk_level,
        "imd_score": round(imd_score),
        "cwc_score": round(cwc_score),
        "explanation": (
            "Final score combines IMD weather warning "
            "information with the CWC historical "
            "water-level score."
        )
    }
@app.route("/api/pre-disaster/final-risk")
def final_pre_disaster_risk():

    imd_result = calculate_imd_risk_score()

    if imd_result.get("status") != "success":
        return jsonify(imd_result), 500

    cwc_result = calculate_cwc_historical_score(
        11.0168,
        76.9558
    )

    if cwc_result.get("status") != "success":
        return jsonify(cwc_result), 500

    final_result = calculate_final_pre_disaster_risk(
        imd_result["imd_score"],
        cwc_result["cwc_score"]
    )

    return jsonify({
        **final_result,
        "imd": imd_result,
        "cwc": cwc_result
    })
@app.route("/api/pre-disaster/test-final")
def test_final_risk():

    imd_score = request.args.get(
        "imd_score",
        type=float
    )

    cwc_score = request.args.get(
        "cwc_score",
        type=float
    )

    if imd_score is None or cwc_score is None:
        return jsonify({
            "status": "error",
            "message":
                "IMD score and CWC score are required"
        }), 400

    result = calculate_final_pre_disaster_risk(
        imd_score,
        cwc_score
    )

    return jsonify(result)
@app.route("/api/pre-disaster/cwc/risk")
def cwc_risk():

    latitude = request.args.get(
        "latitude",
        type=float
    )

    longitude = request.args.get(
        "longitude",
        type=float
    )

    if latitude is None or longitude is None:
        return jsonify({
            "status": "error",
            "message":
                "Latitude and longitude are required"
        }), 400

    return jsonify(
        calculate_cwc_historical_score(
            latitude,
            longitude
        )
    )
@app.route("/api/pre-disaster/cwc/baseline")
def cwc_baseline():

    latitude = request.args.get("latitude", type=float)
    longitude = request.args.get("longitude", type=float)

    if latitude is None or longitude is None:
        return jsonify({
            "status": "error",
            "message": "Latitude and longitude are required"
        }), 400

    return jsonify(
        get_cwc_station_baseline(latitude, longitude)
    )
@app.route("/api/pre-disaster/cwc/trend")
def cwc_trend_test():

    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")

    if not latitude or not longitude:

        return jsonify({
            "status": "error",
            "message": "Latitude and longitude are required."
        }), 400

    try:

        result = get_cwc_trend(
            latitude,
            longitude
        )

        return jsonify({
            "status": "success",
            "cwc_trend": result
        })

    except Exception as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500
@app.route("/api/pre-disaster/cwc/latest")
def cwc_latest_test():

    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")

    if not latitude or not longitude:

        return jsonify({
            "status": "error",
            "message": "Latitude and longitude are required."
        }), 400

    try:

        result = get_latest_cwc_reading(
            latitude,
            longitude
        )

        return jsonify({
            "status": "success",
            "cwc": result
        })

    except Exception as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500
@app.route("/api/pre-disaster/cwc/nearest")
def cwc_nearest_test():

    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")

    if not latitude or not longitude:

        return jsonify({
            "status": "error",
            "message": "Latitude and longitude are required."
        }), 400

    try:

        station = find_nearest_cwc_station(
            latitude,
            longitude
        )

        return jsonify({
            "status": "success",
            "station": station
        })

    except Exception as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500
@app.route("/api/pre-disaster/cwc/columns")
def cwc_columns():

    records = read_cwc_data()

    if not records:
        return jsonify({
            "status": "error",
            "message": "No CWC records found"
        })

    return jsonify({
        "status": "success",
        "columns": list(records[0].keys()),
        "sample": records[0]
    })
@app.route("/api/pre-disaster/cwc/data-test")
def cwc_data_test():

    try:

        records = read_cwc_data()

        return jsonify({
            "status": "success",
            "total_records": len(records),
            "first_record": records[0] if records else None
        })

    except Exception as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500
@app.route("/api/pre-disaster/cwc/test")
def cwc_test():

    return jsonify(test_cwc_file())
@app.route("/api/pre-disaster/imd/<int:district_id>")
def get_imd_warning(district_id):

    url = (
        "https://mausam.imd.gov.in/api/"
        "warnings_district_api.php"
        f"?id={district_id}"
    )

    try:
        response = requests.get(
            url,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        return jsonify({
            "source": "India Meteorological Department",
            "district_id": district_id,
            "data": data
        })

    except Exception as e:

        return jsonify({
            "error": "Unable to retrieve IMD data.",
            "details": str(e)
        }), 502
@app.route("/api/pre-disaster/risk")
def generic_pre_disaster_risk():

    district = request.args.get(
        "district",
        ""
    ).strip().upper()

    # Check district
    if not district:
        return jsonify({
            "status": "error",
            "message": "District is required"
        }), 400

    # Check supported district
    if district not in DISTRICT_COORDINATES:
        return jsonify({
            "status": "error",
            "message": "District is not supported",
            "available_districts": sorted(
                DISTRICT_COORDINATES.keys()
            )
        }), 400

    # Get district coordinates
    latitude, longitude = DISTRICT_COORDINATES[district]

    # -------------------------
    # IMD RISK
    # -------------------------

    imd_result = calculate_imd_district_score(
        district
    )

    if imd_result.get("status") != "success":
        return jsonify(imd_result), 500

    # -------------------------
    # CWC RISK
    # -------------------------

    cwc_result = calculate_cwc_historical_score(
        latitude,
        longitude
    )

    if cwc_result.get("status") != "success":
        return jsonify({
            "status": "error",
            "message": "CWC data unavailable",
            "district": district,
            "imd": imd_result
        }), 500

    # -------------------------
    # FINAL RISK
    # -------------------------

    final_result = calculate_final_pre_disaster_risk(
        imd_result["imd_score"],
        cwc_result["cwc_score"]
    )

    return jsonify({

        "status": "success",

        "district": district,

        "location": {
            "latitude": latitude,
            "longitude": longitude
        },

        "imd": imd_result,

        "cwc": cwc_result,

        "final_score":
            final_result["final_score"],

        "risk_level":
            final_result["risk_level"],

        "explanation":
            final_result["explanation"]
    })
# =========================================================
# IMD DISTRICT WARNING TEST
# =========================================================

def get_imd_warning(district_name):

    url = "https://api.imd.gov.in/api/v1/districtwarning"

    try:

        response = requests.get(
            url,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        # Search for requested district
        if isinstance(data, list):

            for item in data:

                district = str(
                    item.get("District", "")
                ).strip().upper()

                if district == district_name.strip().upper():

                    return {
                        "status": "success",
                        "data": item
                    }

        return {
            "status": "error",
            "message":
                f"{district_name} not found in IMD data"
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
# =========================================================
# IMD PUBLIC DISTRICT WARNING TEST
# =========================================================

# =========================================================
# IMD PUBLIC PAGE - FIND COIMBATORE DATA
# =========================================================

# =========================================================
# IMD PUBLIC DISTRICT WARNING - COIMBATORE
# =========================================================

# =========================================================
# IMD PUBLIC DISTRICT WARNING - COIMBATORE
# =========================================================

# =========================================================
# IMD PUBLIC DISTRICT WARNING - COIMBATORE
# =========================================================

def get_imd_coimbatore_warning():

    url = "https://mausam.imd.gov.in/responsive/districtWiseWarning.php"

    try:

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        html = response.text

        # -------------------------------------------------
        # Find only the COIMBATORE object
        # -------------------------------------------------

        pattern = (
            r'\{\s*'
            r'"title"\s*:\s*"COIMBATORE".*?'
            r'"id"\s*:\s*"([^"]+)".*?'
            r'"color"\s*:\s*"([^"]+)".*?'
            r'"balloonText"\s*:\s*"(.*?)"'
            r'\s*\}'
        )

        match = re.search(
            pattern,
            html,
            re.DOTALL
        )

        if not match:

            return {
                "status": "error",
                "message":
                    "Coimbatore warning data not found"
            }

        district_id = match.group(1)

        color = match.group(2)

        balloon_text = match.group(3)

        # -------------------------------------------------
        # Extract date
        # -------------------------------------------------

        date_match = re.search(
            r"Date:\s*([^:]+)",
            balloon_text
        )

        if date_match:

            warning_date = (
                date_match.group(1).strip()
            )

        else:

            warning_date = None

        # -------------------------------------------------
        # Extract warning text
        # -------------------------------------------------

        warnings = []

        warning_matches = re.findall(
            r"<p>(.*?)<\\/p>",
            balloon_text,
            re.DOTALL
        )

        for warning in warning_matches:

            # Remove HTML tags
            warning = re.sub(
                r"<.*?>",
                "",
                warning
            )

            # Remove escaped slash
            warning = warning.replace(
                "\\/",
                "/"
            )

            warning = warning.strip()

            # Ignore update information
            if warning.startswith(
                "Updated on:"
            ):
                continue

            if warning and warning not in warnings:

                warnings.append(warning)

        # -------------------------------------------------
        # Return Coimbatore data
        # -------------------------------------------------

        return {

            "status": "success",

            "district": "COIMBATORE",

            "district_id": district_id,

            "date": warning_date,

            "color": color,

            "warnings": warnings

        }

    except Exception as e:

        return {

            "status": "error",

            "message": str(e)

        }
def get_imd_district_warning(district_name):

    try:
        response = requests.get(
            "https://mausam.imd.gov.in/responsive/districtWiseWarning.php",
            timeout=15
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "message": "Unable to access IMD warning page"
            }

        html = response.text

        district_name = district_name.strip().upper()

        pattern = (
            r'\{\s*'
            r'"title"\s*:\s*"' +
            re.escape(district_name) +
            r'".*?'
            r'"id"\s*:\s*"([^"]+)".*?'
            r'"color"\s*:\s*"([^"]+)".*?'
            r'"balloonText"\s*:\s*"(.*?)"'
            r'\s*\}'
        )

        match = re.search(
            pattern,
            html,
            re.DOTALL
        )

        if not match:
            return {
                "status": "error",
                "message": (
                    "District not found in IMD warning page"
                ),
                "district": district_name
            }

        district_id = match.group(1)
        color = match.group(2)
        balloon_text = match.group(3)

        date_match = re.search(
            r'Date:\s*(\d{4}-\d{2}-\d{2})',
            balloon_text
        )

        date = (
            date_match.group(1)
            if date_match
            else None
        )

        warning_matches = re.findall(
            r"<p>(.*?)<\\/p>",
            balloon_text,
            re.DOTALL
        )

        warnings = []

        for warning in warning_matches:

            warning = re.sub(
                r"<.*?>",
                "",
                warning
            )

            warning = (
                warning
                .replace("\\/", "/")
                .replace("&amp;", "&")
                .strip()
            )

            if (
                warning
                and not warning.startswith("Updated on:")
                and warning not in warnings
            ):
                warnings.append(warning)

        return {
            "status": "success",
            "district": district_name,
            "district_id": district_id,
            "date": date,
            "imd_color": color,
            "warnings": warnings
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
def calculate_imd_risk_score():

    imd_data = get_imd_coimbatore_warning()

    if imd_data.get("status") != "success":
        return imd_data

    color = imd_data.get("color", "").upper()
    warnings = imd_data.get("warnings", [])

    score = 0

    # IMD warning color
    if color == "#FF0000":
        score = 95

    elif color == "#FFA500":
        score = 75

    elif color == "#FFFF00":
        score = 50

    elif color == "#00FF00":
        score = 10

    else:
        score = 0

    # Increase score if warning contains severe weather
    warning_text = " ".join(warnings).lower()

    if "extremely heavy" in warning_text:
        score += 25

    elif "very heavy" in warning_text:
        score += 20

    elif "heavy rain" in warning_text:
        score += 10

    elif "thunderstorm" in warning_text:
        score += 5

    score = min(score, 100)

    if score >= 75:
        level = "CRITICAL"

    elif score >= 50:
        level = "HIGH"

    elif score >= 25:
        level = "MEDIUM"

    else:
        level = "LOW"

    return {
        "status": "success",
        "district": imd_data["district"],
        "district_id": imd_data["district_id"],
        "date": imd_data["date"],
        "warnings": warnings,
        "imd_color": color,
        "imd_score": score,
        "imd_level": level
    }
def calculate_imd_district_score(district_name):

    imd_data = get_imd_district_warning(
        district_name
    )

    if imd_data.get("status") != "success":
        return imd_data

    color = imd_data.get(
        "imd_color",
        ""
    ).upper()

    warnings = imd_data.get(
        "warnings",
        []
    )

    # -------------------------
    # IMD COLOR SCORE
    # -------------------------

    if color == "#FF0000":
        score = 95

    elif color == "#FFA500":
        score = 75

    elif color == "#FFFF00":
        score = 50

    elif color == "#00FF00":
        score = 10

    else:
        score = 0

    # -------------------------
    # WARNING SEVERITY
    # -------------------------

    warning_text = " ".join(
        warnings
    ).lower()

    if "extremely heavy" in warning_text:
        score += 25

    elif "very heavy" in warning_text:
        score += 20

    elif "heavy rain" in warning_text:
        score += 10

    elif "thunderstorm" in warning_text:
        score += 5

    score = min(score, 100)

    # -------------------------
    # RISK LEVEL
    # -------------------------

    if score >= 75:
        level = "CRITICAL"

    elif score >= 50:
        level = "HIGH"

    elif score >= 25:
        level = "MEDIUM"

    else:
        level = "LOW"

    return {
        **imd_data,
        "imd_score": score,
        "imd_level": level
    }

@app.route("/api/pre-disaster/imd/risk")
def imd_risk():

    return jsonify(
        calculate_imd_risk_score()
    )
@app.route("/api/pre-disaster/imd/coimbatore")
def imd_coimbatore():

    return jsonify(
        get_imd_coimbatore_warning()
    )


@app.route("/api/pre-disaster/imd/test")
def imd_test():

    district = request.args.get(
        "district",
        default="COIMBATORE"
    )

    result = get_imd_warning(
        district
    )

    return jsonify(result)   
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
