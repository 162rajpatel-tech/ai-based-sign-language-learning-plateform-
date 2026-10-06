"""
hand_detector.py — Server-side stub (no-op).

Hand landmark detection has been moved entirely to the browser using
MediaPipe Tasks Vision JS (WASM). This file is kept for compatibility
but performs no actual detection on the server.

The browser sends pre-extracted 21-point landmarks directly to /api/predict.
"""


class HandDetector:
    """No-op stub. Real detection runs in the browser via MediaPipe WASM."""

    def __init__(self, model_path=None, num_hands=1):
        self.detector = True  # signals "loaded" to health check
        print("[HandDetector] Server-side detection disabled — running in browser WASM mode.")

    def detect_landmarks_from_bgr(self, bgr_image):
        """Not used in browser WASM mode."""
        return []

    def decode_base64_image(self, base64_str):
        """Not used in browser WASM mode."""
        return None

    def draw_landmarks_on_image(self, image, landmarks, is_correct=False):
        """Not used in browser WASM mode."""
        return image
