import os
import math
import json 
from google.oauth2 import service_account
from flask import Flask, jsonify
from google.cloud import videointelligence, firestore

#  ✅ Load Firebase credentials from environment variable
service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# ✅ FIRESTORE SETUP
PROJECT_ID = "cedar-spring-455002-r4"
DATABASE_ID = "crowddensity"

 #✅ Initialize Firestore using the credentials
db = firestore.Client(credentials=credentials, project=PROJECT_ID)
#✅ FLASK SETUP
app = Flask(__name__)

# ✅ CONSTANTS
FPS = 1
VIDEO_FILE = "gs://stampede_video/video.mp4"
PENALTY_FACTOR = 10
PRIORITY_WEIGHT = 1  # You can adjust this

# ✅ Fetch exits from Firestore with all fields
def fetch_exits():
    print("🔄 Fetching exit points from Firestore...")
    exit_ref = db.collection("exit_points").stream()
    exits = {}
    for doc in exit_ref:
        data = doc.to_dict()
        exits[data["exit_id"]] = {
            "coordinates": data["coordinates"],
            "congestion_level": data.get("congestion_level", 0),
            "priority": data.get("priority", 0),
            "description": data.get("description", "No Description")
        }
    print(f"✅ Found {len(exits)} exits: {list(exits.keys())}")
    return exits

# ✅ Euclidean Distance
def calculate_distance(coord1, coord2):
    return math.sqrt((coord1["x"] - coord2["x"]) ** 2 + (coord1["y"] - coord2["y"]) ** 2)

# ✅ Best Exit Calculation with Priority
def find_best_exit(person_coords, exits):
    best_exit = None
    best_score = float("inf")
    for exit_id, exit_data in exits.items():
        distance = calculate_distance(person_coords, exit_data["coordinates"])
        congestion = exit_data["congestion_level"]
        priority = exit_data.get("priority", 0)
        score = distance + (congestion * PENALTY_FACTOR) - (priority * PRIORITY_WEIGHT)

        if score < best_score:
            best_score = score
            best_exit = exit_id

    return best_exit

def analyze_crowd_density():
    print(" analyze_crowd_density called (no GCP, no DB)")
    
    # Simulated exits (replace with your real ones later)
    exits = {
        "exit_1": {
            "coordinates": {"x": 0.1, "y": 0.2},
            "congestion_level": 2,
            "priority": 1,
            "description": "Main Gate"
        },
        "exit_2": {
            "coordinates": {"x": 0.8, "y": 0.9},
            "congestion_level": 1,
            "priority": 2,
            "description": "Emergency Exit"
        }
    }

    # Simulated person data
    output_data = [
        {
            "frame": 1,
            "person_id": 1001,
            "x": 0.15,
            "y": 0.22,
            "exit_id": "exit_1",
            "exit_description": exits["exit_1"]["description"]
        },
        {
            "frame": 1,
            "person_id": 1002,
            "x": 0.85,
            "y": 0.88,
            "exit_id": "exit_2",
            "exit_description": exits["exit_2"]["description"]
        },
        {
            "frame": 2,
            "person_id": 1003,
            "x": 0.5,
            "y": 0.5,
            "exit_id": "exit_2",
            "exit_description": exits["exit_2"]["description"]
        }
    ]
    
    print("Crowd density analysis completed!")
    return output_data


# # ✅ Flask Route
# @app.route("/run_crowd_navigation", methods=["GET"])
# def run_crowd_navigation():
#     try:
#         results = analyze_crowd_density()
#         return jsonify({
#             "message": "Crowd navigation completed successfully.",
#             "results": results
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# ✅ Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
