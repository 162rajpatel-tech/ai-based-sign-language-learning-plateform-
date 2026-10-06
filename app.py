from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
from pathlib import Path

from config import HOST, PORT, DEBUG, SIGNS_REFERENCE_PATH
import database
from vision.sign_classifier import SignClassifier

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Initialize database
database.init_db()

# Initialize ML classifier only (no OpenCV / MediaPipe on server)
classifier = SignClassifier()

# Load sign references catalog
with open(SIGNS_REFERENCE_PATH, "r", encoding="utf-8") as f:
    SIGNS_CATALOG = json.load(f)


@app.route("/")
def index():
    """Serves the main interactive learning application."""
    user = database.get_or_create_user("Learner")
    return render_template("index.html", user=user)


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "model_loaded": classifier.model is not None,
        "classes_count": len(classifier.label_encoder.classes_) if classifier.label_encoder else 0,
        "detection_mode": "browser-wasm"
    })


@app.route("/api/lessons", methods=["GET"])
def get_lessons():
    """Returns lessons catalog grouped by categories (Alphabets, Everyday Words)."""
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lessons ORDER BY category, sign_code;")
    rows = cursor.fetchall()
    conn.close()

    lessons_data = []
    for r in rows:
        item = dict(r)
        item["hints"] = json.loads(item["hints"]) if item.get("hints") else []
        item["finger_rules"] = json.loads(item["finger_rules"]) if item.get("finger_rules") else {}
        lessons_data.append(item)

    return jsonify({"lessons": lessons_data, "catalog": SIGNS_CATALOG})


@app.route("/api/predict", methods=["POST"])
def predict():
    """
    ML classification endpoint.

    Accepts JSON body with:
    - `landmarks`: list of 21 {x, y, z} objects pre-extracted by browser MediaPipe WASM
    - `target_sign`: (optional) target sign code for comparison and coaching hints

    Note: Image decoding and hand detection are handled entirely in the browser.
    The server only runs scikit-learn inference on the extracted landmarks.
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    target_sign = data.get("target_sign")
    landmarks = data.get("landmarks")

    # Predict sign posture using ML model only
    prediction_result = classifier.predict(landmarks, target_sign=target_sign)

    # Include landmarks in response for any client-side use
    if landmarks:
        prediction_result["landmarks"] = landmarks

    return jsonify(prediction_result)


@app.route("/api/progress", methods=["GET"])
def get_progress():
    """Returns current user progress, mastery levels, streak, and badges."""
    user = database.get_or_create_user("Learner")
    stats = database.get_user_stats(user["id"])
    return jsonify(stats)


@app.route("/api/progress/attempt", methods=["POST"])
def record_attempt():
    """
    Records a completed practice attempt and updates XP, streak, and badges.
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "No payload"}), 400

    user = database.get_or_create_user("Learner")
    sign_code = data.get("sign_code", "A")
    predicted_sign = data.get("predicted_sign", "")
    confidence = float(data.get("confidence", 0.0))
    is_correct = bool(data.get("is_correct", False))
    duration_ms = int(data.get("duration_ms", 0))

    result = database.record_practice_attempt(
        user_id=user["id"],
        sign_code=sign_code,
        predicted_sign=predicted_sign,
        confidence=confidence,
        is_correct=is_correct,
        duration_ms=duration_ms
    )

    # Return refreshed stats
    refreshed_stats = database.get_user_stats(user["id"])
    result["user_stats"] = refreshed_stats
    return jsonify(result)


@app.route("/api/reset", methods=["POST"])
def reset_progress():
    """Resets practice history for testing."""
    user = database.get_or_create_user("Learner")
    database.reset_user_stats(user["id"])
    refreshed_stats = database.get_user_stats(user["id"])
    return jsonify({"success": True, "user_stats": refreshed_stats})


if __name__ == "__main__":
    print(f"\n🚀 AI Sign Language Learning Platform starting on http://localhost:{PORT}")
    print("   Hand detection: Browser WASM (MediaPipe Tasks Vision JS)")
    print("   ML classification: scikit-learn RandomForest (server)")
    app.run(host=HOST, port=PORT, debug=DEBUG)
