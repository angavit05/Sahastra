from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from google.cloud import firestore
from google.cloud.firestore_v1 import GeoPoint
import google.generativeai as genai
import os
import json
from google.oauth2 import service_account

# ✅ Import internal modules
from ai_analysis import run_ai_crowd_detection
from crowd_navigation import analyze_crowd_density
from user_bestpath import run_user_exit_assignment

# ✅ Initialize Flask App
app = Flask(__name__)
CORS(app)


# ✅ Load Firebase credentials from environment variable
service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# ✅ Firestore Initialization
PROJECT_ID = "cedar-spring-455002-r4"
DATABASE_ID = "crowddensity"

# ✅ Initialize Firestore using the credentials
db = firestore.Client(credentials=credentials, project=PROJECT_ID, database=DATABASE_ID)

# ✅ Gemini API Configuration
genai.configure(api_key=os.environ["GEMINI_API_KEY"])


# ✅ GET Alerts
@app.route('/alerts', methods=['GET'])
def get_alerts():
    try:
        alerts_ref = db.collection('alerts')
        docs = alerts_ref.stream()

        alert_list = []
        for doc in docs:
            data = doc.to_dict()
            alert_list.append({
                'message': data.get('message', 'No message'),
                'latitude': data.get('location').latitude if data.get('location') else None,
                'longitude': data.get('location').longitude if data.get('location') else None,
                'timestamp': data.get('timestamp', 'No timestamp')
            })

        return jsonify(alert_list), 200

    except Exception as e:
        print(f"🔥 Error fetching alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/run_crowd_navigation", methods=["GET"])
def run_crowd_navigation():
    try:
        results = analyze_crowd_density()
        return jsonify({
            "message": "Crowd navigation completed successfully.",
            "results": results
                    }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500




# ✅ Internal Utility — Fetch alert data for Gemini
def fetch_alert_data():
    try:
        alerts_ref = db.collection('alerts')
        docs = alerts_ref.stream()
        alert_data = [doc.to_dict() for doc in docs]
        print(f"📊 Retrieved {len(alert_data)} records from 'alerts' collection.")
        return alert_data
    except Exception as e:
        print(f"🔥 Error fetching alert data: {e}")
        return []


@app.route('/gemini_query', methods=['GET'])
def gemini_query():
    # Here we don't care about the query value for now
    mock_response = {
        "query": "query",
        "ai_response": " The evacuation route is clear."
    }
    return jsonify(mock_response), 200  # Return the mock response



# ✅ AI Crowd Detection Trigger
@app.route('/run_ai_crowd_analysis', methods=['GET'])
def run_ai_crowd_analysis():
    try:
        summary = run_ai_crowd_detection()
        return jsonify({
            "message": "✅ AI-enhanced crowd density analysis completed.",
            "summary": summary
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ Alert POST Route
@app.route('/send_alert', methods=['POST'])
def send_alert():
    data = request.get_json()
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    severity = data.get("severity")
    message = data.get("message")

    if latitude is None or longitude is None or severity is None or message is None:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        alert_ref = db.collection("alerts2").document()
        alert_ref.set({
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "severity": severity,
            "message": message,
            "status": "active",
            "timestamp": datetime.utcnow().isoformat()
        })

        print(f"✅ Alert stored successfully: {alert_ref.id}")
        return jsonify({"message": "Alert sent successfully!", "alert_id": alert_ref.id}), 201

    except Exception as e:
        print(f"❌ Error storing alert: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/send_sos', methods=['POST'])
def send_sos():
    data = request.get_json()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude is None or longitude is None:
        return jsonify({"error": "Missing required fields: latitude, longitude"}), 400

    try:
        sos_ref = db.collection("sos_requests").document()
        sos_ref.set({
            "location": GeoPoint(latitude, longitude),  # ✅ Correct GeoPoint format
            "timestamp": datetime.utcnow().isoformat()  # ⏰ Store ISO timestamp
        })

        print(f"✅ SOS request stored successfully: {sos_ref.id}")
        return jsonify({"message": "SOS request sent successfully!", "sos_id": sos_ref.id}), 201

    except Exception as e:
        print(f"❌ Error storing SOS request: {e}")
        return jsonify({"error": str(e)}), 500
@app.route('/admin/sos_requests', methods=['GET'])
def get_sos_requests():
    try:
        sos_ref = db.collection('sos_requests')
        docs = sos_ref.stream()

        sos_list = []
        for doc in docs:
            data = doc.to_dict()
            location = data.get('location', None)

            if location:
                latitude = location.latitude  # ✅ GeoPoint access
                longitude = location.longitude
            else:
                latitude = None
                longitude = None

            sos_list.append({
                'id': doc.id,
                'timestamp': str(data.get('timestamp', '')),
                'location': {
                    'latitude': latitude,
                    'longitude': longitude
                }
            })

        return jsonify(sos_list), 200

    except Exception as e:
        print(f"🔥 Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return jsonify({
        "message": "🚀 Welcome to the Sahastra API!",
        "available_routes": [
            "/alerts",
            "/run_crowd_navigation",
            "/gemini_query?query=your_question",
            "/run_ai_crowd_analysis",
            "/send_alert",
            "/send_sos",
            "/admin/sos_requests"
        ]
    }), 200


# ✅ Run Server
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
