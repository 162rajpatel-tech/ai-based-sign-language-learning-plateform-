import joblib
import numpy as np
import os
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import SIGN_MODEL_PATH, LABEL_ENCODER_PATH, DEFAULT_CONFIDENCE_THRESHOLD, SIGNS_REFERENCE_PATH
from vision.feature_extractor import FeatureExtractor

class SignClassifier:
    """
    Inference pipeline for classifying 21-point hand landmark postures into ASL signs,
    providing direct sign-to-text translation, and generating related educational text.
    """

    def __init__(self, model_path=None, encoder_path=None):
        self.model_path = model_path or SIGN_MODEL_PATH
        self.encoder_path = encoder_path or LABEL_ENCODER_PATH
        self.model = None
        self.label_encoder = None
        self.extractor = FeatureExtractor()
        self.catalog = {}
        self._load_catalog()
        self._load_model()

    def _load_catalog(self):
        if os.path.exists(SIGNS_REFERENCE_PATH):
            with open(SIGNS_REFERENCE_PATH, "r", encoding="utf-8") as f:
                self.catalog = json.load(f)

    def _load_model(self):
        if not os.path.exists(self.model_path) or not os.path.exists(self.encoder_path):
            print(f"Warning: Model or label encoder not found at {self.model_path}. Please run train_model.py first.")
            return
        self.model = joblib.load(self.model_path)
        self.label_encoder = joblib.load(self.encoder_path)
        print(f"SignClassifier loaded successfully with {len(self.label_encoder.classes_)} classes.")

    def predict(self, landmarks, target_sign=None):
        """
        Classifies given landmarks and compares against target sign if provided.
        Returns prediction details, probabilities, and coaching tips.
        """
        if not landmarks or len(landmarks) < 21:
            return {
                "hand_detected": False,
                "predicted_sign": None,
                "confidence": 0.0,
                "is_match": False,
                "top_predictions": [],
                "hints": ["Place your hand in front of the camera."],
                "finger_states": {}
            }

        # Extract features
        feats = self.extractor.extract_features(landmarks)
        if feats is None or self.model is None or self.label_encoder is None:
            return {
                "hand_detected": True,
                "predicted_sign": "UNKNOWN",
                "confidence": 0.0,
                "is_match": False,
                "top_predictions": [],
                "hints": ["Model not ready or landmarks insufficient."],
                "finger_states": {}
            }

        # Predict probabilities
        feats_2d = feats.reshape(1, -1)
        probas = self.model.predict_proba(feats_2d)[0]
        classes = self.label_encoder.classes_

        # Sort top 3
        top_indices = np.argsort(probas)[::-1][:3]
        top_predictions = [
            {"sign": str(classes[idx]), "confidence": round(float(probas[idx]), 3)}
            for idx in top_indices
        ]

        best_idx = top_indices[0]
        predicted_sign = str(classes[best_idx])
        confidence = round(float(probas[best_idx]), 3)

        # Handle linguistic equivalent aliases (e.g. V and PEACE)
        is_match = False
        target_norm = target_sign.upper() if target_sign else None

        if target_norm:
            if predicted_sign == target_norm:
                is_match = True
            elif target_norm in ["V", "PEACE"] and predicted_sign in ["V", "PEACE"]:
                is_match = True
                predicted_sign = target_norm # normalize to user expectation

        # Finger states and coaching hints
        finger_states = self.extractor.analyze_finger_states(landmarks)
        hints = self.extractor.generate_coaching_hints(target_norm, landmarks) if target_norm else []

        # Retrieve comprehensive text related to sign given by user
        sign_meta = self.catalog.get(predicted_sign, {})
        related_text = {
            "sign": predicted_sign,
            "name": sign_meta.get("name", f"Sign {predicted_sign}"),
            "translation": predicted_sign.replace("_", " "),
            "category": sign_meta.get("category", "alphabet"),
            "description": sign_meta.get("description", ""),
            "usage": sign_meta.get("usage", "Standard American Sign Language communication."),
            "example_sentence": sign_meta.get("example_sentence", ""),
            "confusable_with": sign_meta.get("confusable_with", ""),
            "related_words": sign_meta.get("related_words", []),
            "fun_fact": sign_meta.get("fun_fact", "")
        }

        return {
            "hand_detected": True,
            "predicted_sign": predicted_sign,
            "confidence": confidence,
            "is_match": is_match,
            "target_sign": target_norm,
            "top_predictions": top_predictions,
            "finger_states": finger_states,
            "hints": hints,
            "related_text": related_text
        }
