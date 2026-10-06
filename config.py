import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Model Asset Paths
HAND_LANDMARKER_PATH = MODELS_DIR / "hand_landmarker.task"
SIGN_MODEL_PATH = MODELS_DIR / "sign_model.joblib"
LABEL_ENCODER_PATH = MODELS_DIR / "label_encoder.joblib"
SIGNS_REFERENCE_PATH = DATA_DIR / "signs_reference.json"
DATASET_CSV_PATH = DATA_DIR / "sign_landmarks_dataset.csv"

# Database Path (use /tmp in serverless environments like Vercel)
DB_PATH = Path(os.environ.get("DB_PATH", "/tmp/sign_language.db" if os.environ.get("VERCEL") else BASE_DIR / "sign_language.db"))

# Recognition Hyperparameters
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5
DEFAULT_CONFIDENCE_THRESHOLD = 0.65
HOLD_CONFIRMATION_SECONDS = 1.5  # Time to hold sign steadily for success confirmation

# Server Settings
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True
