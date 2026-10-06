from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import json
import time
import cv2
from pathlib import Path

from config import HOST, PORT, DEBUG, HAND_LANDMARKER_PATH, SIGNS_REFERENCE_PATH
import database
from vision.hand_detector import HandDetector
from vision.sign_classifier import SignClassifier

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Initialize database
database.init_db()

# Initialize Computer Vision & AI models
detector = HandDetector(model_path=HAND_LANDMARKER_PATH)
classifier = SignClassifier()

# Load sign references catalog
with open(SIGNS_REFERENCE_PATH, "r", encoding="utf-8") as f:
    SIGNS_CATALOG = json.load(f)

# Global camera for optional server-side streaming
server_camera = None

def get_server_camera():
    global server_camera
    if server_camera is None:
        server_camera = cv2.VideoCapture(0)
    return server_camera

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
        "detector_loaded": detector.detector is not None,
        "classes_count": len(classifier.label_encoder.classes_) if classifier.label_encoder else 0
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
    Main prediction endpoint.
    Accepts:
    - Base64 video frame (`image`) OR
    - Pre-extracted 21 landmark points (`landmarks`)
    - `target_sign` (optional target for comparison and hints)
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    target_sign = data.get("target_sign")
    landmarks = data.get("landmarks")

    # If raw image base64 provided, run MediaPipe detection on server
    if not landmarks and data.get("image"):
        bgr_frame = detector.decode_base64_image(data.get("image"))
        if bgr_frame is not None:
            detected_hands = detector.detect_landmarks_from_bgr(bgr_frame)
            if detected_hands:
                landmarks = detected_hands[0]

    # Predict sign posture
    prediction_result = classifier.predict(landmarks, target_sign=target_sign)

    # Attach landmarks in response for client-side visual feedback if server processed the image
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

def generate_video_stream():
    """Generator for server-side OpenCV video streaming with MediaPipe overlays."""
    cap = get_server_camera()
    while True:
        success, frame = cap.read()
        if not success:
            time.sleep(0.05)
            continue

        # Flip horizontally for natural mirror feel
        frame = cv2.flip(frame, 1)

        # Detect landmarks
        detected_hands = detector.detect_landmarks_from_bgr(frame)
        if detected_hands:
            landmarks = detected_hands[0]
            detector.draw_landmarks_on_image(frame, landmarks, is_correct=False)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route("/video_feed")
def video_feed():
    """MJPEG stream endpoint for server-side camera viewing."""
    try:
        return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print(f"\n🚀 AI Sign Language Learning Platform starting on http://localhost:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
