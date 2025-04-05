import os
import time
import math
import json 
from datetime import datetime
from google.cloud import videointelligence, firestore

# ✅ Load Firebase credentials from environment variable
service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
credentials = service_account.Credentials.from_service_account_info(service_account_info)


# ✅ GOOGLE CLOUD FIRESTORE SETUP
PROJECT_ID = "cedar-spring-455002-r4"
DATABASE_ID = "crowddensity"

# ✅ Initialize Firestore using the credentials
db = firestore.Client(credentials=credentials, project=PROJECT_ID, database=DATABASE_ID)


# ✅ CONSTANTS
FPS = 1  # Reduced Frames per second to process fewer frames
VIDEO_FILE = "gs://stampede_video/video.mp4"
PENALTY_FACTOR = 10  # Adjust this to balance congestion impact


# ✅ Cache to track last assigned exits
person_last_exit = {}


def fetch_exits():
   """Fetches exits from Firestore, including their coordinates and congestion level."""
   print("🔄 Fetching exit points from Firestore...")
   exit_ref = db.collection("exit_points").stream()
   exits = {}
   for doc in exit_ref:
       data = doc.to_dict()
       exits[data["exit_id"]] = {
           "coordinates": data["coordinates"],
           "congestion_level": data.get("congestion_level", 0)
       }
   print(f"✅ Found {len(exits)} exits: {list(exits.keys())}")
   return exits


def calculate_distance(coord1, coord2):
   """Calculates Euclidean distance between two points."""
   return math.sqrt((coord1["x"] - coord2["x"]) ** 2 + (coord1["y"] - coord2["y"]) ** 2)


def find_best_exit(person_coords, exits):
   """Finds the best exit based on distance and congestion level."""
   best_exit = None
   best_score = float("inf")
   print(f"\n🔍 Finding best exit for Person at {person_coords}")


   for exit_id, exit_data in exits.items():
       distance = calculate_distance(person_coords, exit_data["coordinates"])
       congestion = exit_data["congestion_level"]
       weighted_score = distance + (congestion * PENALTY_FACTOR)


       print(f"➡ Exit {exit_id}: Distance = {distance:.2f}, Congestion = {congestion}, Score = {weighted_score:.2f}")


       if weighted_score < best_score:
           best_score = weighted_score
           best_exit = exit_id


   print(f"✅ Best Exit Selected: {best_exit}\n")
   return best_exit


def store_person_exit(frame_number, person_id, best_exit):
   """Stores new/different exits for a person in Firestore with timestamp."""
   global person_last_exit


   if person_id in person_last_exit and person_last_exit[person_id] == best_exit:
       print(f"🔁 Person {person_id}: Exit unchanged → {best_exit} (not stored again)")
       return


   # Update the cache with new exit
   person_last_exit[person_id] = best_exit


   # Composite document ID to avoid overwrites
   doc_id = f"{person_id}_{frame_number}"
   doc_ref = db.collection("person_exits").document(doc_id)


   data = {
       "person_id": person_id,
       "frame_number": frame_number,
       "current_exit": best_exit,
       "last_updated": firestore.SERVER_TIMESTAMP
   }
   doc_ref.set(data)
   print(f"📥 Stored → Person {person_id} | Frame {frame_number} | Exit: {best_exit}")


def analyze_crowd_density():
   """Analyzes the video for crowd density and assigns exits to people."""
   client = videointelligence.VideoIntelligenceServiceClient()
   features = [videointelligence.Feature.OBJECT_TRACKING]
   request = videointelligence.AnnotateVideoRequest(input_uri=VIDEO_FILE, features=features)


   print("🔄 Processing video... (this may take a while)")
   operation = client.annotate_video(request=request)
   result = operation.result(timeout=600)
   annotations = result.annotation_results[0].object_annotations


   exits = fetch_exits()
   frame_counts = {}


   for annotation in annotations:
       if annotation.entity.description.lower() == "person":
           person_id = annotation.track_id


           for frame in annotation.frames:
               time_offset = frame.time_offset
               seconds = time_offset.seconds + (time_offset.microseconds / 1e6)
               frame_number = int(seconds * FPS)


               box = frame.normalized_bounding_box
               x, y = (box.left + box.right) / 2, (box.top + box.bottom) / 2


               if frame_number not in frame_counts:
                   frame_counts[frame_number] = 0
               frame_counts[frame_number] += 1


               print(f"🎥 Processing Frame {frame_number}: Person {person_id} at ({x:.2f}, {y:.2f})")


               person_coords = {"x": x, "y": y}
               best_exit = find_best_exit(person_coords, exits)
               store_person_exit(frame_number, person_id, best_exit)


   print("✅ Crowd density analysis with exit assignment completed!")

def run_user_exit_assignment():
    analyze_crowd_density()