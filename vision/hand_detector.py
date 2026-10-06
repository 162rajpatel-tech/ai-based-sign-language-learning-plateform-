import cv2
import numpy as np
import base64
import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from config import HAND_LANDMARKER_PATH, MIN_DETECTION_CONFIDENCE, MIN_TRACKING_CONFIDENCE

# Landmark Connections in Hand Skeleton for Drawing
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
    (0, 17)                                # Palm base
]

class HandDetector:
    def __init__(self, model_path=None, num_hands=1):
        self.model_path = str(model_path or HAND_LANDMARKER_PATH)
        self.num_hands = num_hands
        self.detector = None
        self._init_detector()

    def _init_detector(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"MediaPipe Hand Landmarker model not found at {self.model_path}")
        
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=self.num_hands,
            min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def detect_landmarks_from_bgr(self, bgr_image):
        """
        Runs MediaPipe hand landmark detection on an OpenCV BGR image.
        Returns a list of hand landmarks (each being a list of 21 dicts with x, y, z).
        """
        if self.detector is None or bgr_image is None:
            return []

        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
        
        result = self.detector.detect(mp_image)
        
        detected_hands = []
        if result.hand_landmarks:
            for hand in result.hand_landmarks:
                landmarks = []
                for lm in hand:
                    landmarks.append({
                        "x": float(lm.x),
                        "y": float(lm.y),
                        "z": float(lm.z)
                    })
                detected_hands.append(landmarks)
                
        return detected_hands

    def decode_base64_image(self, base64_str):
        """Decodes a base64 encoded data URI string to an OpenCV BGR image."""
        try:
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            img_bytes = base64.b64decode(base64_str)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            print(f"Error decoding base64 image: {e}")
            return None

    def draw_landmarks_on_image(self, image, landmarks, is_correct=False):
        """
        Draws visual hand skeleton and landmark keypoints onto an OpenCV frame.
        Uses glowing cyan/emerald for correct posture and neon amber for default.
        """
        h, w, _ = image.shape
        line_color = (0, 242, 100) if is_correct else (255, 170, 0)      # BGR
        point_color = (255, 255, 255)
        joint_color = (0, 200, 255)

        # Convert normalized coords to pixel points
        pts = [(int(lm["x"] * w), int(lm["y"] * h)) for lm in landmarks]

        # Draw bones
        for start_idx, end_idx in HAND_CONNECTIONS:
            if start_idx < len(pts) and end_idx < len(pts):
                cv2.line(image, pts[start_idx], pts[end_idx], line_color, 3, cv2.LINE_AA)

        # Draw joints
        for i, pt in enumerate(pts):
            radius = 6 if i in [4, 8, 12, 16, 20] else 4 # Fingertips larger
            cv2.circle(image, pt, radius, joint_color, -1, cv2.LINE_AA)
            cv2.circle(image, pt, radius + 1, point_color, 1, cv2.LINE_AA)

        return image
