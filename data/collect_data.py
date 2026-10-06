"""
Standalone Data Collection Script for AI-Based Sign Language Platform.
Allows developers/users to collect custom real-world training samples directly
from their webcam using OpenCV and MediaPipe.
"""

import cv2
import csv
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from vision.hand_detector import HandDetector
from vision.feature_extractor import FeatureExtractor
from config import DATA_DIR, HAND_LANDMARKER_PATH

def run_collector():
    print("=" * 60)
    print("AI Sign Language Data Collector")
    print("=" * 60)
    
    sign_label = input("Enter meaningful word gesture to record (e.g. HELLO, THANK_YOU, PLEASE, HELP): ").strip().upper()
    if not sign_label:
        print("Invalid label. Exiting.")
        return

    num_samples = input("Number of samples to collect (default: 50): ").strip()
    num_samples = int(num_samples) if num_samples.isdigit() else 50

    output_csv = DATA_DIR / "custom_recorded_landmarks.csv"
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    detector = HandDetector(model_path=HAND_LANDMARKER_PATH)
    extractor = FeatureExtractor()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("\nInstructions:")
    print(" - Press 'SPACE' to start/pause recording samples.")
    print(" - Press 'Q' or 'ESC' to exit anytime.")
    print(" - Adjust hand angles and slight distances while recording to build diversity.")
    
    recording = False
    collected = 0

    while collected < num_samples:
        ret, frame = cap.read()
        if not ret:
            break

        # Mirror view for natural interaction
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        detected_hands = detector.detect_landmarks_from_bgr(frame)
        hand_detected = len(detected_hands) > 0

        if hand_detected:
            landmarks = detected_hands[0]
            detector.draw_landmarks_on_image(frame, landmarks, is_correct=recording)

            if recording:
                feats = extractor.extract_features(landmarks)
                if feats is not None:
                    row = list(feats) + [sign_label]
                    
                    # Append directly to CSV
                    file_exists = output_csv.exists()
                    with open(output_csv, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            headers = [f"f_{i}" for i in range(len(feats))] + ["label"]
                            writer.writerow(headers)
                        writer.writerow(row)

                    collected += 1
                    time.sleep(0.04) # ~25 fps capture rate

        # Status text overlay
        status_text = f"Recording: {collected}/{num_samples}" if recording else "PAUSED (Press SPACE to record)"
        color = (0, 255, 0) if recording else (0, 200, 255)
        cv2.putText(frame, f"Sign: {sign_label} | {status_text}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        if not hand_detected:
            cv2.putText(frame, "No Hand Detected!", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Sign Language Data Collector", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            recording = not recording
        elif key in [ord('q'), 27]: # Q or ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nFinished collection! Saved {collected} samples to: {output_csv}")

if __name__ == "__main__":
    run_collector()
