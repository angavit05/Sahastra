from flask import Flask, request, jsonify
import google.generativeai as genai
from google.cloud import firestore
import os

# 🔐 Set Firebase credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\hp\Documents\key2.json"

# ✅ Configure Gemini & Firestore
genai.configure(api_key="AIzaSyDiXk-adAjaRlneqr_i4bO3i1CoRmeLRtY")

PROJECT_ID = "cedar-spring-455002-r4"
DATABASE_ID = "crowddensity"
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

# ✅ Flask App
app = Flask(__name__)

# ✅ Function to fetch ALL crowd alert data
def get_crowd_data():
    alerts_ref = db.collection('alerts')
    docs = alerts_ref.stream()
    crowd_data = [doc.to_dict() for doc in docs]
    print(f"📊 Retrieved {len(crowd_data)} records from Firestore.")
    return crowd_data

# ✅ Gemini query function
def ask_gemini(query, crowd_data):
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    context = f"""
    You are an AI assistant analyzing crowd movement data.
    Here is the latest crowd data:\n{crowd_data}\n
    Answer the admin query based on this data:
    """
    response = model.generate_content(context + query)
    return response.text

# ✅ API Route
@app.route("/gemini_query", methods=["GET"])
def gemini_query():
    user_query = request.args.get("query")
    if not user_query:
        return jsonify({"error": "Missing 'query' parameter"}), 400

    crowd_data = get_crowd_data()
    if not crowd_data:
        return jsonify({"query": user_query, "ai_response": "⚠️ No crowd data found in Firestore."})

    ai_response = ask_gemini(user_query, crowd_data)
    return jsonify({"query": user_query, "ai_response": ai_response})

# ✅ Start Flask Server
if __name__ == "__main__":
    print("🚀 Running Gemini NLP Flask API")
    app.run(host="0.0.0.0", port=5000)
