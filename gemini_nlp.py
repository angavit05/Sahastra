from flask import Flask, request, jsonify
import google.generativeai as genai
from google.cloud import firestore
import os
import json 
from google.oauth2 import service_account
# ✅ Load Firebase credentials from environment variable
service_account_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# ✅ Configure Gemini & Firestore

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
PROJECT_ID = "cedar-spring-455002-r4"
DATABASE_ID = "crowddensity"

# ✅ Initialize Firestore using the credentials
db = firestore.Client(credentials=credentials, project=PROJECT_ID, database=DATABASE_ID)

# ✅ Flask App
app = Flask(__name__)

# ✅ Function to fetch ALL crowd alert data
def get_crowd_data():
    alerts_ref = db.collection('alerts')
    docs = alerts_ref.stream()
    crowd_data = [doc.to_dict() for doc in docs]
    print(f"📊 Retrieved {len(crowd_data)} records from Firestore.")
    return crowd_data

def ask_gemini(query, crowd_data):
    print("🔮 Mock Gemini response triggered.")
    return f"🤖 This is a mock AI response to your query: '{query}' based on {len(crowd_data)} crowd records."

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
