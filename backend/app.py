import re
from flask import Flask, request, jsonify, send_from_directory
import os
from flask_cors import CORS
import sqlite3
from datetime import datetime, timezone
import requests
import csv
import math
import xml.etree.ElementTree as ET

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
    cwc_score,
    sachet_score=0,
    sachet_alert_found=False
):

    # Base risk from IMD + CWC
    base_score = (
        (imd_score * 0.60)
        +
        (cwc_score * 0.40)
    )

    base_score = round(
        max(
            0,
            min(
                100,
                base_score
            )
        )
    )

    # If an active SACHET alert exists,
    # do not allow the official alert signal
    # to be diluted by the base score.
    if sachet_alert_found:

        final_score = max(
            base_score,
            sachet_score
        )

    else:

        final_score = base_score

    final_score = round(
        max(
            0,
            min(
                100,
                final_score
            )
        )
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

        "base_score":
            base_score,

        "sachet_score":
            round(sachet_score),

        "sachet_alert_found":
            sachet_alert_found,

        "final_score":
            final_score,

        "risk_level":
            risk_level,

        "explanation": (
            "Base risk combines IMD weather "
            "warning information and CWC "
            "historical water-level data. "
            "When an active SACHET alert is "
            "present, the final score uses the "
            "higher of the base risk and the "
            "SACHET alert score."
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
def get_sachet_alerts(district_name=None):

    feed_url = (
        "https://sachet.ndma.gov.in/"
        "cap_public_website/rss/rss_india.xml"
    )

    try:

        # -------------------------------------------------
        # 1. Connect to SACHET RSS feed
        # -------------------------------------------------

        try:

            response = requests.get(
                feed_url,
                timeout=(5, 15)
            )

        except requests.exceptions.Timeout:

            return {
                "status": "error",
                "error_type": "timeout",
                "message": (
                    "SACHET server did not respond within "
                    "the allowed time. Please try again later."
                )
            }

        except requests.exceptions.ConnectionError:

            return {
                "status": "error",
                "error_type": "connection",
                "message": (
                    "Unable to connect to the SACHET server. "
                    "Please try again later."
                )
            }

        # -------------------------------------------------
        # 2. Check HTTP response
        # -------------------------------------------------

        if response.status_code != 200:

            return {
                "status": "error",
                "message": (
                    "Unable to access SACHET RSS feed"
                ),
                "http_status": response.status_code
            }

        # -------------------------------------------------
        # 3. Parse RSS XML
        # -------------------------------------------------

        root = ET.fromstring(
            response.content
        )

        alerts = []

        # -------------------------------------------------
        # 4. Prepare district filter
        # -------------------------------------------------

        district_filter = None

        if district_name:

            district_filter = (
                district_name
                .strip()
                .lower()
            )

        # -------------------------------------------------
        # 5. Read RSS alerts
        # -------------------------------------------------

        for item in root.findall(".//item"):

            title_element = item.find("title")
            link_element = item.find("link")
            date_element = item.find("pubDate")

            title = (
                title_element.text.strip()
                if title_element is not None
                and title_element.text
                else ""
            )

            link = (
                link_element.text.strip()
                if link_element is not None
                and link_element.text
                else ""
            )

            published = (
                date_element.text.strip()
                if date_element is not None
                and date_element.text
                else ""
            )

            # -------------------------------------------------
            # 6. If no district is selected,
            #    return RSS alerts normally
            # -------------------------------------------------

            if not district_filter:

                alerts.append({
                    "title": title,
                    "published": published,
                    "link": link
                })

                continue

            # -------------------------------------------------
            # 7. CAP link is required for accurate
            #    geographic matching
            # -------------------------------------------------

            if not link:
                continue

            cap_result = get_sachet_cap_alert(
                link
            )

            if cap_result.get("status") != "success":
                continue

            # -------------------------------------------------
            # 8. Get the official SACHET affected area
            #
            #    This comes from CAP <areaDesc>
            # -------------------------------------------------

            area = (
                cap_result.get(
                    "area",
                    ""
                )
                .strip()
            )

            # -------------------------------------------------
            # 9. Do NOT use headline or title for
            #    district matching.
            #
            #    Only the official affected-area field
            #    is used.
            # -------------------------------------------------

            if not area:
                continue

            area_lower = area.lower()

            # -------------------------------------------------
            # 10. Check whether the selected district
            #     is actually present in the affected area
            # -------------------------------------------------

            if district_filter not in area_lower:
                continue

            # -------------------------------------------------
            # 11. Add the verified matching alert
            # -------------------------------------------------

            alerts.append({

                "title": title,

                "published": published,

                "link": link,

                "identifier": cap_result.get(
                    "identifier",
                    ""
                ),

                "sender": cap_result.get(
                    "sender",
                    ""
                ),

                "sent": cap_result.get(
                    "sent",
                    ""
                ),

                "alert_status": cap_result.get(
                    "alert_status",
                    ""
                ),

                "message_type": cap_result.get(
                    "message_type",
                    ""
                ),

                "event": cap_result.get(
                    "event",
                    ""
                ),

                "urgency": cap_result.get(
                    "urgency",
                    ""
                ),

                "severity": cap_result.get(
                    "severity",
                    ""
                ),

                "certainty": cap_result.get(
                    "certainty",
                    ""
                ),

                "effective": cap_result.get(
                    "effective",
                    ""
                ),

                "onset": cap_result.get(
                    "onset",
                    ""
                ),

                "expires": cap_result.get(
                    "expires",
                    ""
                ),

                "headline": cap_result.get(
                    "headline",
                    ""
                ),

                "instruction": cap_result.get(
                    "instruction",
                    ""
                ),

                "area": area,

                "source_url": cap_result.get(
                    "source_url",
                    link
                )
            })

        # -------------------------------------------------
        # 12. Return results
        # -------------------------------------------------

        return {
            "status": "success",
            "source": "SACHET - NDMA",
            "feed_url": feed_url,
            "district_filter": district_name,
            "alert_count": len(alerts),
            "alert_found": len(alerts) > 0,
            "alerts": alerts
        }

    except ET.ParseError:

        return {
            "status": "error",
            "error_type": "xml_parse",
            "message": (
                "SACHET returned invalid XML"
            )
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": "unknown",
            "message": str(e)
        }
@app.route("/api/pre-disaster/sachet/alerts")
def sachet_all_alerts():

    feed_url = (
        "https://sachet.ndma.gov.in/"
        "cap_public_website/rss/rss_india.xml"
    )

    try:

        response = requests.get(
            feed_url,
            timeout=20
        )

        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": "Unable to access SACHET RSS feed",
                "http_status": response.status_code
            }), 500

        root = ET.fromstring(
            response.content
        )

        alerts = []

        # Supported Tamil Nadu districts
        tamil_nadu_districts = {
            "Ariyalur",
            "Chengalpattu",
            "Chennai",
            "Coimbatore",
            "Cuddalore",
            "Dharmapuri",
            "Dindigul",
            "Erode",
            "Kallakurichi",
            "Kanchipuram",
            "Kanniyakumari",
            "Karur",
            "Krishnagiri",
            "Madurai",
            "Mayiladuthurai",
            "Nagapattinam",
            "Namakkal",
            "Perambalur",
            "Pudukkottai",
            "Ramanathapuram",
            "Ranipet",
            "Salem",
            "Sivaganga",
            "Tenkasi",
            "Thanjavur",
            "The Nilgiris",
            "Theni",
            "Thoothukudi",
            "Tiruchirappalli",
            "Tirunelveli",
            "Tirupathur",
            "Tiruppur",
            "Tiruvallur",
            "Tiruvannamalai",
            "Tiruvarur",
            "Vellore",
            "Viluppuram",
            "Virudhunagar"
        }

        for item in root.findall(".//item"):

            title_element = item.find("title")
            link_element = item.find("link")
            date_element = item.find("pubDate")

            title = (
                title_element.text.strip()
                if title_element is not None
                and title_element.text
                else ""
            )

            link = (
                link_element.text.strip()
                if link_element is not None
                and link_element.text
                else ""
            )

            published = (
                date_element.text.strip()
                if date_element is not None
                and date_element.text
                else ""
            )

            if not link:
                continue

            cap_result = get_sachet_cap_alert(link)

            if cap_result.get("status") != "success":
                continue

            # Get SACHET area and headline
            area_text = cap_result.get(
                "area",
                ""
            ).strip()

            headline_text = cap_result.get(
                "headline",
                ""
            ).strip()

            # Search both area and headline
            search_text = (
                area_text
                + " "
                + headline_text
            )

            # Find only supported Tamil Nadu districts
            affected_districts = []

            for district in tamil_nadu_districts:

                if district.lower() in search_text.lower():

                    affected_districts.append(
                        district
                    )

            alerts.append({
                "title": title,
                "published": published,
                "link": link,

                "identifier":
                    cap_result.get(
                        "identifier",
                        ""
                    ),

                "sender":
                    cap_result.get(
                        "sender",
                        ""
                    ),

                "sent":
                    cap_result.get(
                        "sent",
                        ""
                    ),

                "alert_status":
                    cap_result.get(
                        "alert_status",
                        ""
                    ),

                "message_type":
                    cap_result.get(
                        "message_type",
                        ""
                    ),

                "event":
                    cap_result.get(
                        "event",
                        ""
                    ),

                "urgency":
                    cap_result.get(
                        "urgency",
                        ""
                    ),

                "severity":
                    cap_result.get(
                        "severity",
                        ""
                    ),

                "certainty":
                    cap_result.get(
                        "certainty",
                        ""
                    ),

                "effective":
                    cap_result.get(
                        "effective",
                        ""
                    ),

                "onset":
                    cap_result.get(
                        "onset",
                        ""
                    ),

                "expires":
                    cap_result.get(
                        "expires",
                        ""
                    ),

                "headline":
                    cap_result.get(
                        "headline",
                        ""
                    ),

                "description":
                    cap_result.get(
                        "description",
                        ""
                    ),

                "instruction":
                    cap_result.get(
                        "instruction",
                        ""
                    ),

                "area":
                    cap_result.get(
                        "area",
                        ""
                    ),

                "affected_districts":
                    affected_districts,

                "source_url":
                    cap_result.get(
                        "source_url",
                        link
                    )
            })

        return jsonify({
            "status": "success",
            "source": "SACHET - NDMA",
            "feed_url": feed_url,
            "alert_count": len(alerts),
            "alerts": alerts
        })

    except ET.ParseError:

        return jsonify({
            "status": "error",
            "message": "SACHET returned invalid XML"
        }), 500

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
def get_sachet_cap_alert(cap_url):

    try:

        response = requests.get(
            cap_url,
            timeout=20
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "message": "Unable to access SACHET CAP alert",
                "http_status": response.status_code
            }

        root = ET.fromstring(
            response.content
        )

        def get_text(path):

            element = root.find(path)

            if element is not None and element.text:
                return element.text.strip()

            return ""

        identifier = get_text(
            ".//{*}identifier"
        )

        sender = get_text(
            ".//{*}sender"
        )

        sent = get_text(
            ".//{*}sent"
        )

        alert_status = get_text(
            ".//{*}status"
        )

        message_type = get_text(
            ".//{*}msgType"
        )

        event = get_text(
            ".//{*}event"
        )

        urgency = get_text(
            ".//{*}urgency"
        )

        severity = get_text(
            ".//{*}severity"
        )

        certainty = get_text(
            ".//{*}certainty"
        )

        effective = get_text(
            ".//{*}effective"
        )

        onset = get_text(
            ".//{*}onset"
        )

        expires = get_text(
            ".//{*}expires"
        )

        headline = get_text(
            ".//{*}headline"
        )

        description = get_text(
            ".//{*}description"
        )

        instruction = get_text(
            ".//{*}instruction"
        )

        area = get_text(
            ".//{*}areaDesc"
        )

        return {
            "status": "success",
            "identifier": identifier,
            "sender": sender,
            "sent": sent,
            "alert_status": alert_status,
            "message_type": message_type,
            "event": event,
            "urgency": urgency,
            "severity": severity,
            "certainty": certainty,
            "effective": effective,
            "onset": onset,
            "expires": expires,
            "headline": headline,
            "description": description,
            "instruction": instruction,
            "area": area,
            "source_url": cap_url
        }

    except ET.ParseError:

        return {
            "status": "error",
            "message": "Invalid SACHET CAP XML"
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
def get_active_sachet_alerts(district_name):

    result = get_sachet_alerts(
        district_name
    )

    if result.get("status") != "success":
        return result

    active_alerts = []

    current_time = datetime.now(
        timezone.utc
    )

    for alert in result.get(
        "alerts",
        []
    ):

        # -------------------------------------------------
        # 1. Check alert status
        # -------------------------------------------------

        alert_status = (
            alert.get(
                "alert_status",
                ""
            )
            .strip()
            .lower()
        )

        # Only Actual alerts are considered.
        if alert_status != "actual":
            continue

        # -------------------------------------------------
        # 2. Read SACHET timestamps
        # -------------------------------------------------

        expires_text = (
            alert.get(
                "expires",
                ""
            )
            .strip()
        )

        effective_text = (
            alert.get(
                "effective",
                ""
            )
            .strip()
        )

        onset_text = (
            alert.get(
                "onset",
                ""
            )
            .strip()
        )

        # -------------------------------------------------
        # 3. Parse timestamps
        # -------------------------------------------------

        expires_time = None
        effective_time = None
        onset_time = None

        if expires_text:

            try:
                expires_time = datetime.fromisoformat(
                    expires_text
                )

            except ValueError:
                continue

        if effective_text:

            try:
                effective_time = datetime.fromisoformat(
                    effective_text
                )

            except ValueError:
                continue

        if onset_text:

            try:
                onset_time = datetime.fromisoformat(
                    onset_text
                )

            except ValueError:
                continue

        # -------------------------------------------------
        # 4. Require an expiry time
        # -------------------------------------------------

        # An alert without an expiry time cannot safely
        # be treated as an active alert.
        if expires_time is None:
            continue

        # -------------------------------------------------
        # 5. Check expiry
        # -------------------------------------------------

        # Alert is inactive when expiry time has arrived.
        if current_time >= expires_time:
            continue

        # -------------------------------------------------
        # 6. Check effective time
        # -------------------------------------------------

        if (
            effective_time is not None
            and current_time < effective_time
        ):
            continue

        # -------------------------------------------------
        # 7. Check onset time
        # -------------------------------------------------

        if (
            onset_time is not None
            and current_time < onset_time
        ):
            continue

        # -------------------------------------------------
        # 8. Alert is genuinely active
        # -------------------------------------------------

        active_alerts.append(
            alert
        )

    return {
        "status": "success",
        "district": district_name,
        "alert_found": (
            len(active_alerts) > 0
        ),
        "alert_count": len(active_alerts),
        "alerts": active_alerts
    }
def classify_sachet_disaster_threat(alert):
    """
    Classifies an active SACHET alert for public display.

    This is an application-level classification.
    It is NOT an official NDMA/SACHET risk score.
    """

    event = (
        alert.get("event", "")
        .strip()
        .lower()
    )

    headline = (
        alert.get("headline", "")
        .strip()
        .lower()
    )

    severity = (
        alert.get("severity", "")
        .strip()
        .upper()
    )

    urgency = (
        alert.get("urgency", "")
        .strip()
        .upper()
    )

    certainty = (
        alert.get("certainty", "")
        .strip()
        .upper()
    )

    # Combine official event information
    # for classification.
    hazard_text = (
        event + " " + headline
    )

    # -------------------------------------------------
    # 1. HIGH-CONCERN DISASTER HAZARDS
    # -------------------------------------------------

    critical_hazards = [
        "tsunami",
        "storm surge",
        "landslide",
        "flash flood",
        "flood",
        "cyclone",
        "tropical cyclone",
        "severe cyclonic storm",
        "very severe cyclonic storm",
        "extremely severe cyclonic storm"
    ]

    for hazard in critical_hazards:

        if hazard in hazard_text:

            if (
                severity in [
                    "EXTREME",
                    "SEVERE"
                ]
                or urgency == "IMMEDIATE"
            ):

                return {
                    "threat_level": "CRITICAL",
                    "public_alert": True,
                    "reason": (
                        "SACHET reports a potentially "
                        "dangerous disaster-related hazard."
                    )
                }

            return {
                "threat_level": "WARNING",
                "public_alert": True,
                "reason": (
                    "SACHET reports a disaster-related "
                    "hazard that requires preparedness."
                )
            }

    # -------------------------------------------------
    # 2. SEVERE WEATHER
    # -------------------------------------------------

    severe_weather = [
        "very heavy rain",
        "extremely heavy rain",
        "heavy rainfall",
        "heavy rain",
        "thunderstorm",
        "lightning",
        "strong wind",
        "gale",
        "heat wave",
        "cold wave"
    ]

    for hazard in severe_weather:

        if hazard in hazard_text:

            if severity == "EXTREME":

                return {
                    "threat_level": "CRITICAL",
                    "public_alert": True,
                    "reason": (
                        "SACHET reports an extreme "
                        "weather hazard."
                    )
                }

            if (
                severity == "SEVERE"
                and certainty in [
                    "OBSERVED",
                    "LIKELY"
                ]
            ):

                return {
                    "threat_level": "WARNING",
                    "public_alert": True,
                    "reason": (
                        "SACHET reports severe weather "
                        "that may require preparedness."
                    )
                }

            if (
                urgency == "IMMEDIATE"
                and certainty in [
                    "OBSERVED",
                    "LIKELY"
                ]
            ):

                return {
                    "threat_level": "PREPARE",
                    "public_alert": True,
                    "reason": (
                        "SACHET reports an immediate "
                        "weather-related concern."
                    )
                }

            # Ordinary/moderate weather should NOT
            # create a public disaster warning.
            return {
                "threat_level": "NORMAL",
                "public_alert": False,
                "reason": (
                    "The current SACHET weather alert "
                    "does not meet the application's "
                    "disaster-warning threshold."
                )
            }

    # -------------------------------------------------
    # 3. OTHER SERIOUS HAZARDS
    # -------------------------------------------------

    other_hazards = [
        "earthquake",
        "avalanche",
        "forest fire",
        "wildfire",
        "dam break",
        "dam failure",
        "chemical",
        "industrial accident",
        "nuclear",
        "radiological"
    ]

    for hazard in other_hazards:

        if hazard in hazard_text:

            if severity == "EXTREME":

                return {
                    "threat_level": "CRITICAL",
                    "public_alert": True,
                    "reason": (
                        "SACHET reports an extreme "
                        "hazard condition."
                    )
                }

            if severity == "SEVERE":

                return {
                    "threat_level": "WARNING",
                    "public_alert": True,
                    "reason": (
                        "SACHET reports a severe "
                        "hazard condition."
                    )
                }

            return {
                "threat_level": "PREPARE",
                "public_alert": True,
                "reason": (
                    "SACHET reports a potentially "
                    "hazardous event."
                )
            }

    # -------------------------------------------------
    # 4. DEFAULT
    # -------------------------------------------------

    return {
        "threat_level": "NORMAL",
        "public_alert": False,
        "reason": (
            "No disaster-level condition was "
            "identified from the active SACHET alert."
        )
    }
def get_sachet_preparedness_guidance(alert):
    """
    Generates application-level preparedness guidance
    based on the hazard described in an active SACHET alert.

    This guidance is informational and does not replace
    official instructions from authorities.
    """

    event = (
        alert.get("event", "")
        .strip()
        .lower()
    )

    headline = (
        alert.get("headline", "")
        .strip()
        .lower()
    )

    hazard_text = event + " " + headline

    guidance = []

    # -------------------------------------------------
    # FLOOD / HEAVY RAIN
    # -------------------------------------------------
    if (
        "flood" in hazard_text
        or "flash flood" in hazard_text
        or "heavy rain" in hazard_text
        or "heavy rainfall" in hazard_text
        or "very heavy rain" in hazard_text
        or "extremely heavy rain" in hazard_text
        or "moderate rain" in hazard_text
    ):
        guidance.extend([
            "Avoid unnecessary travel during heavy rainfall.",
            "Stay away from flooded and waterlogged roads.",
            "Keep essential items and important documents in a safe, elevated place.",
            "Keep your phone, power bank and emergency contacts ready."
        ])

    # -------------------------------------------------
    # LIGHTNING / THUNDERSTORM
    # -------------------------------------------------
    if (
        "lightning" in hazard_text
        or "thunderstorm" in hazard_text
        or "thundershower" in hazard_text
    ):
        guidance.extend([
            "During lightning, stay indoors and avoid open areas.",
            "Avoid standing under isolated trees or near exposed electrical equipment.",
            "If outdoors, move to a safe enclosed building as soon as possible."
        ])

    # -------------------------------------------------
    # CYCLONE / STRONG WIND
    # -------------------------------------------------
    if (
        "cyclone" in hazard_text
        or "strong wind" in hazard_text
        or "gale" in hazard_text
        or "storm surge" in hazard_text
    ):
        guidance.extend([
            "Stay indoors and follow official cyclone instructions.",
            "Secure loose objects around your home or building.",
            "Keep essential supplies, a charged phone and a power bank ready.",
            "Avoid coastal and other areas specifically identified by authorities as unsafe."
        ])

    # -------------------------------------------------
    # HEAT WAVE
    # -------------------------------------------------
    if (
        "heat wave" in hazard_text
        or "heatwave" in hazard_text
    ):
        guidance.extend([
            "Avoid unnecessary outdoor activity during the hottest part of the day.",
            "Drink sufficient water and stay hydrated.",
            "Stay in a cool or well-ventilated place whenever possible.",
            "Check on elderly people, children and others who may be vulnerable to heat."
        ])

    # -------------------------------------------------
    # COLD WAVE
    # -------------------------------------------------
    if "cold wave" in hazard_text:
        guidance.extend([
            "Stay warm and avoid prolonged exposure to cold conditions.",
            "Keep adequate warm clothing and essential supplies ready.",
            "Check on elderly people, children and vulnerable persons."
        ])

    # -------------------------------------------------
    # LANDSLIDE
    # -------------------------------------------------
    if "landslide" in hazard_text:
        guidance.extend([
            "Avoid unstable slopes and areas identified as landslide-prone.",
            "Follow evacuation instructions issued by local authorities.",
            "Do not enter areas affected by landslides or falling debris.",
            "Keep emergency contacts and essential supplies ready."
        ])

    # -------------------------------------------------
    # EARTHQUAKE
    # -------------------------------------------------
    if "earthquake" in hazard_text:
        guidance.extend([
            "Stay calm and follow official emergency instructions.",
            "Move away from damaged buildings and structures.",
            "Keep emergency supplies and communication devices ready.",
            "Avoid entering damaged buildings until authorities declare them safe."
        ])

    # -------------------------------------------------
    # WILDFIRE / FOREST FIRE
    # -------------------------------------------------
    if (
        "wildfire" in hazard_text
        or "forest fire" in hazard_text
        or "forestfire" in hazard_text
    ):
        guidance.extend([
            "Stay away from the affected fire area.",
            "Follow evacuation instructions from local authorities.",
            "Avoid travelling toward areas affected by smoke or fire.",
            "Keep emergency contacts and essential supplies ready."
        ])

    # -------------------------------------------------
    # AVALANCHE
    # -------------------------------------------------
    if "avalanche" in hazard_text:
        guidance.extend([
            "Avoid avalanche-prone areas.",
            "Follow evacuation and travel instructions issued by authorities.",
            "Do not enter restricted or unsafe areas."
        ])

    # -------------------------------------------------
    # GENERIC FALLBACK
    # -------------------------------------------------
    if not guidance:
        guidance = [
            "Follow the official instructions issued by the relevant authorities.",
            "Keep basic emergency supplies ready.",
            "Keep your phone, power bank and emergency contacts available.",
            "Continue monitoring official SACHET alerts for updates."
        ]

    # Remove duplicate guidance while preserving order.
    unique_guidance = list(dict.fromkeys(guidance))

    return unique_guidance
def calculate_sachet_alert_score(district_name):

    result = get_active_sachet_alerts(
        district_name
    )

    # -------------------------------------------------
    # 1. SACHET SERVER / CONNECTION ERROR
    # -------------------------------------------------

    if result.get("status") != "success":

        return {
            "status": "error",
            "district": district_name,

            "alert_found": False,
            "alert_count": 0,

            "sachet_score": None,
            "sachet_level": "DATA UNAVAILABLE",

            "threat_level": "DATA UNAVAILABLE",
            "public_alert": False,

            "threat_reason": (
                "The SACHET alert service could not "
                "be reached, so a public disaster "
                "assessment cannot be made."
            ),

            "message": result.get(
                "message",
                "Unable to retrieve SACHET alerts"
            ),

            "alerts": []
        }

    # -------------------------------------------------
    # 2. GET ONLY ACTIVE ALERTS
    # -------------------------------------------------

    active_alerts = result.get(
        "alerts",
        []
    )

    # -------------------------------------------------
    # 3. NO ACTIVE ALERT
    # -------------------------------------------------

    if not active_alerts:

        return {
            "status": "success",
            "district": district_name,

            "alert_found": False,
            "alert_count": 0,

            # Internal score
            "sachet_score": 0,
            "sachet_level": "NO ACTIVE ALERT",

            # Public assessment
            "threat_level": "NORMAL",
            "public_alert": False,

            "threat_reason": (
                "No active matching SACHET alert "
                "was found for this district."
            ),

            "score_explanation": (
                "No active matching SACHET alert "
                "was found for this district."
            ),

            "preparedness_guidance": [
                "Keep basic emergency supplies ready.",
                "Keep emergency contacts available.",
                "Follow instructions issued by the relevant authorities.",
                "Continue monitoring official SACHET alerts."
            ],

            "alerts": []
        }

    # -------------------------------------------------
    # 4. SCORE VALUES
    # -------------------------------------------------

    severity_scores = {

        "EXTREME": 100,

        "SEVERE": 85,

        "MODERATE": 60,

        "MINOR": 35,

        "UNKNOWN": 0
    }

    urgency_scores = {

        "IMMEDIATE": 100,

        "EXPECTED": 70,

        "FUTURE": 40,

        "PAST": 0,

        "UNKNOWN": 0
    }

    certainty_scores = {

        "OBSERVED": 100,

        "LIKELY": 80,

        "POSSIBLE": 50,

        "UNLIKELY": 20,

        "UNKNOWN": 0
    }

    # -------------------------------------------------
    # 5. CALCULATE SCORE FOR EACH ACTIVE ALERT
    # -------------------------------------------------

    scored_alerts = []

    highest_score = 0

    for alert in active_alerts:

        severity = (
            alert.get(
                "severity",
                "UNKNOWN"
            )
            .strip()
            .upper()
        )

        urgency = (
            alert.get(
                "urgency",
                "UNKNOWN"
            )
            .strip()
            .upper()
        )

        certainty = (
            alert.get(
                "certainty",
                "UNKNOWN"
            )
            .strip()
            .upper()
        )

        # -------------------------------------------------
        # Get individual scores
        # -------------------------------------------------

        severity_score = severity_scores.get(
            severity,
            0
        )

        urgency_score = urgency_scores.get(
            urgency,
            0
        )

        certainty_score = certainty_scores.get(
            certainty,
            0
        )

        # -------------------------------------------------
        # Calculate internal alert score
        # -------------------------------------------------

        alert_score = (

            severity_score * 0.50

            + urgency_score * 0.30

            + certainty_score * 0.20
        )

        # Keep score between 0 and 100

        alert_score = round(
            max(
                0,
                min(
                    100,
                    alert_score
                )
            )
        )

        # -------------------------------------------------
        # Convert score into internal level
        # -------------------------------------------------

        if alert_score >= 75:

            alert_level = "CRITICAL"

        elif alert_score >= 50:

            alert_level = "HIGH"

        elif alert_score >= 25:

            alert_level = "MEDIUM"

        else:

            alert_level = "LOW"

        # -------------------------------------------------
        # DISASTER THREAT CLASSIFICATION
        # -------------------------------------------------

        threat = classify_sachet_disaster_threat(
            alert
        )

        # -------------------------------------------------
        # HAZARD-SPECIFIC PREPAREDNESS GUIDANCE
        # -------------------------------------------------

        preparedness_guidance = (
            get_sachet_preparedness_guidance(
                alert
            )
        )

        # -------------------------------------------------
        # Add score + threat + guidance information
        # -------------------------------------------------

        scored_alert = {

            **alert,

            "severity_score":
                severity_score,

            "urgency_score":
                urgency_score,

            "certainty_score":
                certainty_score,

            "sachet_score":
                alert_score,

            "sachet_level":
                alert_level,

            "threat_level":
                threat.get(
                    "threat_level",
                    "NORMAL"
                ),

            "public_alert":
                threat.get(
                    "public_alert",
                    False
                ),

            "threat_reason":
                threat.get(
                    "reason",
                    ""
                ),

            "preparedness_guidance":
                preparedness_guidance
        }

        scored_alerts.append(
            scored_alert
        )

        # Keep highest active alert score

        highest_score = max(
            highest_score,
            alert_score
        )

    # -------------------------------------------------
    # 6. DETERMINE OVERALL INTERNAL LEVEL
    # -------------------------------------------------

    if highest_score >= 75:

        overall_level = "CRITICAL"

    elif highest_score >= 50:

        overall_level = "HIGH"

    elif highest_score >= 25:

        overall_level = "MEDIUM"

    else:

        overall_level = "LOW"

    # -------------------------------------------------
    # 7. DETERMINE OVERALL PUBLIC THREAT
    # -------------------------------------------------

    public_alerts = [

        alert
        for alert in scored_alerts
        if alert.get(
            "public_alert",
            False
        )
    ]

    if public_alerts:

        threat_priority = {
            "CRITICAL": 4,
            "WARNING": 3,
            "PREPARE": 2,
            "NORMAL": 1
        }

        overall_threat = max(
            public_alerts,
            key=lambda alert:
                threat_priority.get(
                    alert.get(
                        "threat_level",
                        "NORMAL"
                    ),
                    1
                )
        )

        overall_threat_level = (
            overall_threat.get(
                "threat_level",
                "NORMAL"
            )
        )

        overall_public_alert = True

    else:

        overall_threat_level = "NORMAL"

        overall_public_alert = False

    # -------------------------------------------------
    # 8. FINAL RESULT
    # -------------------------------------------------

    return {

        "status": "success",

        "district": district_name,

        "alert_found": True,

        "alert_count": len(
            scored_alerts
        ),

        # Internal score
        "sachet_score":
            highest_score,

        "sachet_level":
            overall_level,

        # Public-facing disaster classification
        "threat_level":
            overall_threat_level,

        "public_alert":
            overall_public_alert,

        "score_explanation": (
            "This internal SACHET alert score "
            "combines official alert severity, "
            "urgency and certainty. It is not "
            "an official NDMA/SACHET risk score."
        ),

        "alerts":
            scored_alerts
    }
def calculate_sachet_cap_score(cap_url):

    cap_data = get_sachet_cap_alert(
        cap_url
    )

    if cap_data.get("status") != "success":
        return cap_data

    severity_scores = {
        "EXTREME": 100,
        "SEVERE": 85,
        "MODERATE": 60,
        "MINOR": 35,
        "UNKNOWN": 0
    }

    urgency_scores = {
        "IMMEDIATE": 100,
        "EXPECTED": 70,
        "FUTURE": 40,
        "PAST": 0,
        "UNKNOWN": 0
    }

    certainty_scores = {
        "OBSERVED": 100,
        "LIKELY": 80,
        "POSSIBLE": 50,
        "UNLIKELY": 20,
        "UNKNOWN": 0
    }

    severity = (
        cap_data.get(
            "severity",
            "UNKNOWN"
        )
        .upper()
    )

    urgency = (
        cap_data.get(
            "urgency",
            "UNKNOWN"
        )
        .upper()
    )

    certainty = (
        cap_data.get(
            "certainty",
            "UNKNOWN"
        )
        .upper()
    )

    severity_score = severity_scores.get(
        severity,
        0
    )

    urgency_score = urgency_scores.get(
        urgency,
        0
    )

    certainty_score = certainty_scores.get(
        certainty,
        0
    )

    alert_score = (
        severity_score * 0.50
        +
        urgency_score * 0.30
        +
        certainty_score * 0.20
    )

    alert_score = round(
        max(
            0,
            min(
                100,
                alert_score
            )
        )
    )

    if alert_score >= 75:

        alert_level = "CRITICAL"

    elif alert_score >= 50:

        alert_level = "HIGH"

    elif alert_score >= 25:

        alert_level = "MEDIUM"

    else:

        alert_level = "LOW"

    return {
        **cap_data,

        "severity_score":
            severity_score,

        "urgency_score":
            urgency_score,

        "certainty_score":
            certainty_score,

        "sachet_score":
            alert_score,

        "sachet_level":
            alert_level,

        "score_explanation": (
            "SACHET alert score combines "
            "CAP severity, urgency and "
            "certainty."
        )
    }
@app.route("/api/pre-disaster/sachet/debug")
def sachet_debug():

    feed_url = (
        "https://sachet.ndma.gov.in/"
        "cap_public_website/rss/rss_india.xml"
    )

    try:

        response = requests.get(
            feed_url,
            timeout=20
        )

        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": "Unable to access SACHET RSS feed",
                "http_status": response.status_code
            }), 500

        root = ET.fromstring(
            response.content
        )

        total_rss_alerts = 0
        cap_links_found = 0
        cap_success = 0
        cap_failed = 0

        title_matches = 0
        headline_matches = 0
        area_matches = 0
        any_location_matches = 0

        matching_alerts = []

        sample_alerts = []

        search_text = "coimbatore"

        for item in root.findall(".//item"):

            total_rss_alerts += 1

            title_element = item.find("title")
            link_element = item.find("link")

            title = (
                title_element.text.strip()
                if title_element is not None
                and title_element.text
                else ""
            )

            link = (
                link_element.text.strip()
                if link_element is not None
                and link_element.text
                else ""
            )

            if not link:
                continue

            cap_links_found += 1

            cap_result = get_sachet_cap_alert(
                link
            )

            if cap_result.get("status") != "success":

                cap_failed += 1

                continue

            cap_success += 1

            headline = (
                cap_result.get(
                    "headline",
                    ""
                )
            )

            area = (
                cap_result.get(
                    "area",
                    ""
                )
            )

            title_lower = title.lower()
            headline_lower = headline.lower()
            area_lower = area.lower()

            title_contains = (
                search_text
                in title_lower
            )

            headline_contains = (
                search_text
                in headline_lower
            )

            area_contains = (
                search_text
                in area_lower
            )

            any_location_contains = (
                title_contains
                or headline_contains
                or area_contains
            )

            if title_contains:
                title_matches += 1

            if headline_contains:
                headline_matches += 1

            if area_contains:
                area_matches += 1

            if any_location_contains:
                any_location_matches += 1

                matching_alerts.append({
                    "title": title,
                    "headline": headline,
                    "area": area,
                    "event":
                        cap_result.get(
                            "event",
                            ""
                        ),
                    "severity":
                        cap_result.get(
                            "severity",
                            ""
                        ),
                    "urgency":
                        cap_result.get(
                            "urgency",
                            ""
                        ),
                    "certainty":
                        cap_result.get(
                            "certainty",
                            ""
                        ),
                    "link": link
                })

            if len(sample_alerts) < 10:

                sample_alerts.append({
                    "title": title,
                    "headline": headline,
                    "area": area,

                    "title_contains_coimbatore":
                        title_contains,

                    "headline_contains_coimbatore":
                        headline_contains,

                    "area_contains_coimbatore":
                        area_contains,

                    "event":
                        cap_result.get(
                            "event",
                            ""
                        ),

                    "severity":
                        cap_result.get(
                            "severity",
                            ""
                        ),

                    "urgency":
                        cap_result.get(
                            "urgency",
                            ""
                        ),

                    "certainty":
                        cap_result.get(
                            "certainty",
                            ""
                        ),

                    "link": link
                })

        return jsonify({

            "status": "success",

            "search_location":
                "COIMBATORE",

            "feed_url":
                feed_url,

            "total_rss_alerts":
                total_rss_alerts,

            "cap_links_found":
                cap_links_found,

            "cap_success":
                cap_success,

            "cap_failed":
                cap_failed,

            "title_matches":
                title_matches,

            "headline_matches":
                headline_matches,

            "area_matches":
                area_matches,

            "any_location_matches":
                any_location_matches,

            "matching_alerts":
                matching_alerts,

            "sample_alerts":
                sample_alerts
        })

    except ET.ParseError:

        return jsonify({
            "status": "error",
            "message": "SACHET returned invalid XML"
        }), 500

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
@app.route("/api/pre-disaster/sachet/active")
def sachet_active():

    district = request.args.get(
        "district",
        ""
    ).strip()

    if not district:

        return jsonify({
            "status": "error",
            "message": "District is required"
        }), 400

    result = get_active_sachet_alerts(
        district
    )

    if result.get("status") != "success":

        return jsonify(result), 500

    return jsonify(result)
@app.route("/api/pre-disaster/sachet/score")
def sachet_score_by_district():

    district = request.args.get(
        "district",
        ""
    ).strip()

    if not district:

        return jsonify({
            "status": "error",
            "message": "District is required"
        }), 400

    result = calculate_sachet_alert_score(
        district
    )

    if result.get("status") != "success":

        return jsonify(result), 500

    return jsonify(result)
@app.route("/api/pre-disaster/sachet/score")
def sachet_score():

    cap_url = request.args.get(
        "url",
        ""
    ).strip()

    if not cap_url:

        return jsonify({
            "status": "error",
            "message": "CAP URL is required"
        }), 400

    result = calculate_sachet_alert_score(
        cap_url
    )

    if result.get("status") != "success":

        return jsonify(result), 500

    return jsonify(result)
@app.route("/api/pre-disaster/sachet")
def sachet_alerts():

    district = request.args.get(
        "district",
        ""
    ).strip()

    result = get_sachet_alerts(
        district if district else None
    )

    if result.get("status") != "success":
        return jsonify(result), 500

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

    if not district:

        return jsonify({
            "status": "error",
            "message": "District is required"
        }), 400

    if district not in DISTRICT_COORDINATES:

        return jsonify({
            "status": "error",
            "message": "District is not supported",
            "available_districts":
                sorted(
                    DISTRICT_COORDINATES.keys()
                )
        }), 400

    # --------------------------------
    # SACHET ONLY
    # --------------------------------

    sachet_result = calculate_sachet_alert_score(
        district
    )

    if sachet_result.get("status") != "success":

        return jsonify({
            "status": "error",
            "district": district,
            "message": (
                "Unable to retrieve "
                "SACHET alert information"
            ),
            "sachet": sachet_result
        }), 500

    # --------------------------------
    # FINAL RESPONSE
    # --------------------------------

    return jsonify({

        "status": "success",

        "district": district,

        "source": "SACHET - NDMA",

        "sachet": {

    "alert_found":
        sachet_result.get(
            "alert_found",
            False
        ),

    "alert_count":
        sachet_result.get(
            "alert_count",
            0
        ),

    # Internal explainable score
    "sachet_score":
        sachet_result.get(
            "sachet_score",
            0
        ),

    # Internal score level
    "sachet_level":
        sachet_result.get(
            "sachet_level",
            "NO ACTIVE ALERT"
        ),

    # Public-facing disaster assessment
    "threat_level":
        sachet_result.get(
            "threat_level",
            "NORMAL"
        ),

    "public_alert":
        sachet_result.get(
            "public_alert",
            False
        ),

    "threat_reason":
        (
            sachet_result.get(
                "alerts",
                [{}]
            )[0].get(
                "threat_reason",
                ""
            )
            if sachet_result.get(
                "alerts",
                []
            )
            else ""
        ),
    
    "preparedness_guidance": (
    sachet_result.get("alerts", [{}])[0].get(
        "preparedness_guidance",
        []
    )
    if sachet_result.get("alerts", [])
    else []
),
    "score_explanation":
        sachet_result.get(
            "score_explanation",
            ""
        ),

    "alerts":
        sachet_result.get(
            "alerts",
            []
        )
},

        "explanation": (
            "Pre-disaster alert assessment "
            "is based on active SACHET "
            "alerts from NDMA. The system "
            "does not treat the absence of "
            "a SACHET alert as proof that "
            "no disaster will occur."
        )
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
