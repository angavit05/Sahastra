import os
import time
from datetime import datetime
from google.cloud import videointelligence, firestore
import google.generativeai as genai

# ✅ GOOGLE CLOUD AUTHENTICATION
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\hp\crowd_alert_api\key2.json"

# ✅ GOOGLE CLOUD SERVICES SETUP
PROJECT_ID = "cedar-spring-455002-r4"
DATABASE_ID = "crowddensity"
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

# ✅ GOOGLE CLOUD GEMINI API SETUP
genai.configure(api_key="AIzaSyDiXk-adAjaRlneqr_i4bO3i1CoRmeLRtY")

# ✅ CONSTANTS
THRESHOLD_COUNT = 18  # People count threshold
THRESHOLD_DURATION = 1  # In seconds (testing mode)
FPS = 10  # Frames per second
FRAME_LIMIT = THRESHOLD_DURATION * FPS
VIDEO_FILE = "gs://stampede_video/video.mp4"

# ✅ DEFAULT LOCATION
DEFAULT_LOCATION = {"latitude": 19.0760, "longitude": 72.8777}  # Mumbai, India

# ✅ Tracking Variables
high_crowd_frames = []
last_alert_time = None


def generate_ai_alert_message():
    """Generates a natural language alert message using Gemini AI."""
    prompt = (
        f"A high crowd density of {THRESHOLD_COUNT}+ people has been detected for {THRESHOLD_DURATION} seconds. "
        "Describe this situation in a human-friendly way, emphasizing urgency."
    )

    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    response = model.generate_content(prompt)

    return response.text if response and response.text else "⚠️ High crowd density detected! Please take necessary precautions."


def send_alert():
    """Sends an AI-enhanced alert to Firestore when the threshold is exceeded."""
    global high_crowd_frames

    if not high_crowd_frames:
        return

    ai_message = generate_ai_alert_message()

    alert_data = {
        "timestamp": datetime.utcnow(),
        "message": ai_message,
        "threshold": THRESHOLD_COUNT,
        "duration_exceeded": THRESHOLD_DURATION,
        "frame_numbers": high_crowd_frames.copy(),
        "location": firestore.GeoPoint(DEFAULT_LOCATION["latitude"], DEFAULT_LOCATION["longitude"]),
        "status": "active"
    }

    alerts_ref = db.collection("alerts").document(str(int(time.time())))
    alerts_ref.set(alert_data)

    # 🔍 Debug Terminal Output
    print("🚨 ALERT GENERATED 🚨")
    print(f"🔴 Timestamp: {alert_data['timestamp']}")
    print(f"📌 People Count Threshold: {THRESHOLD_COUNT}")
    print(f"⏳ Duration Exceeded: {THRESHOLD_DURATION} seconds")
    print(f"🎥 Frames Triggering Alert: {alert_data['frame_numbers']}")
    print(f"📍 Location: {DEFAULT_LOCATION}")
    print(f"📝 AI-Generated Message: {ai_message}")

    high_crowd_frames.clear()


def update_firestore(frame_number, people_count):
    """Updates Firestore with frame data and checks for alert conditions."""
    global last_alert_time, high_crowd_frames

    # ✅ Store frame data in Firestore
    doc_ref = db.collection("crowd_data").document(str(frame_number))
    doc_ref.set({
        "frame_number": frame_number,
        "people_count": people_count,
        "location": firestore.GeoPoint(DEFAULT_LOCATION["latitude"], DEFAULT_LOCATION["longitude"])
    })

    print(f"✅ Firestore Updated: Frame {frame_number}, People Count: {people_count}")

    # ✅ Check alert condition
    if people_count >= THRESHOLD_COUNT:
        high_crowd_frames.append(frame_number)
        if len(high_crowd_frames) >= FRAME_LIMIT:
            if last_alert_time is None or (time.time() - last_alert_time > THRESHOLD_DURATION):
                send_alert()
                last_alert_time = time.time()
    else:
        high_crowd_frames.clear()


def analyze_crowd_density():
    """Analyzes the video for crowd density using Google Video Intelligence API."""
    print("🔄 Starting AI Crowd Analysis...")
    client = videointelligence.VideoIntelligenceServiceClient()
    features = [videointelligence.Feature.OBJECT_TRACKING]
    request = videointelligence.AnnotateVideoRequest(input_uri=VIDEO_FILE, features=features)

    operation = client.annotate_video(request=request)
    print("📽️ Processing video... (this may take a while)")

    result = operation.result(timeout=600)
    annotations = result.annotation_results[0].object_annotations

    frame_counts = {}

    for annotation in annotations:
        if annotation.entity.description.lower() == "person":
            for frame in annotation.frames:
                time_offset = frame.time_offset
                seconds = time_offset.seconds + (time_offset.microseconds / 1e6)
                frame_number = int(seconds * FPS)

                frame_counts[frame_number] = frame_counts.get(frame_number, 0) + 1

    for frame_number, count in sorted(frame_counts.items()):
        update_firestore(frame_number, count)

    print("✅ AI-enhanced crowd density analysis completed!")


# ✅ Callable by Flask
def run_ai_crowd_detection():
    analyze_crowd_density()


# ✅ Direct CLI Run (if needed)
if __name__ == "__main__":
    run_ai_crowd_detection()
