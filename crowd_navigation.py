import os
import math
from flask import Flask, jsonify
from google.cloud import videointelligence, firestore

# ✅ GOOGLE CLOUD AUTHENTICATION
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\hp\Documents\key2.json"

# ✅ FIRESTORE SETUP
PROJECT_ID = "cedar-spring-455002-r4"
DATABASE_ID = "crowddensity"
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

# ✅ FLASK SETUP
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

# ✅ Main Video Analysis
def analyze_crowd_density():
    client = videointelligence.VideoIntelligenceServiceClient()
    features = [videointelligence.Feature.OBJECT_TRACKING]
    request = videointelligence.AnnotateVideoRequest(input_uri=VIDEO_FILE, features=features)

    print("🔄 Processing video...")
    operation = client.annotate_video(request=request)
    result = operation.result(timeout=600)
    annotations = result.annotation_results[0].object_annotations

    exits = fetch_exits()
    output_data = []

    for annotation in annotations:
        if annotation.entity.description.lower() == "person":
            person_id = annotation.track_id
            for frame in annotation.frames:
                time_offset = frame.time_offset
                seconds = time_offset.seconds + (time_offset.microseconds / 1e6)
                frame_number = int(seconds * FPS)

                box = frame.normalized_bounding_box
                x, y = (box.left + box.right) / 2, (box.top + box.bottom) / 2
                person_coords = {"x": x, "y": y}
                best_exit = find_best_exit(person_coords, exits)

                exit_data = exits[best_exit]
                description = exit_data.get("description", "No Description")

                output_data.append({
                    "frame": frame_number,
                    "person_id": person_id,
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "exit_id": best_exit,
                    "exit_description": description
                })

    print("✅ Crowd density analysis with exit assignment completed!")
    return output_data

# ✅ Flask Route
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

# ✅ Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
