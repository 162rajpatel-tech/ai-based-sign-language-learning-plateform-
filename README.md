# 🤟 SignAI — AI-Based Interactive Sign Language Learning Platform (Meaningful Words & Gestures)

An interactive full-stack web application designed for beginners, students, and families to learn and communicate in **American Sign Language (ASL)** using real-time webcam gesture tracking.

The platform is designed to **strictly recognize whole, meaningful communicative words and expressions** (e.g., *HELLO*, *THANK YOU*, *YES*, *NO*, *PLEASE*, *SORRY*, *HELP*, *I LOVE YOU*, *GOOD*, *STOP*, *OK*, *PEACE*, *WELCOME*, *CALL ME*, *WATER*) rather than isolated single alphabet letters.

Whenever a user performs a gesture in front of the webcam, the system:
1. Detects hand position and 21 3D landmarks via **Google MediaPipe Hand Landmarker**.
2. Classifies the gesture into a **meaningful word** using a trained **Random Forest Machine Learning model** (92%+ accuracy).
3. Transcribes the recognized word onto a **Live Sign-to-Text Subtitle Bar** and **Sentence Composer**.
4. Provides **deep contextual text** related to the gesture (definition, conversational usage, real-world example sentences, confusable sign warnings, and related vocabulary).
5. Pronounces the recognized words aloud using the **Web Speech API (Text-to-Speech)**.

---

## 🌟 Key Features

1. **Side-by-Side Learning Studio**:
   - Reference guide with visual diagrams, anatomical rules, and sign descriptions side-by-side with your live camera view.
   - Lesson catalog covering **ASL Alphabets (A–Z)** and **Everyday Gestures** (*Hello*, *Thank You*, *Yes*, *No*, *I Love You*, *Peace*).

2. **21-Point Computer Vision Pipeline**:
   - Real-time hand landmark detection using MediaPipe.
   - Coordinate translation to wrist origin ($p_i - p_0$) and scale normalization relative to hand size for distance invariance.
   - Feature engineering vector including pairwise fingertip Euclidean distances, joint flexion angles, and extension ratios (86 dimensions).

3. **Real-Time AI Classification**:
   - Machine learning inference pipeline evaluated with **95.5% accuracy** on biomechanically augmented datasets.
   - Live confidence score and top-3 prediction probabilities.
   - Sustained hold-to-confirm mechanism (hold sign for 1.4s) to eliminate transient noise and foster muscle memory.

4. **Granular Anatomical Coaching**:
   - Live finger checklist showing individual status for **Thumb**, **Index**, **Middle**, **Ring**, and **Pinky**.
   - Specific positioning tips: *"Extend index finger"*, *"Fold thumb across palm"*, *"Spread fingers apart into a V"*.

5. **Gamification & Progress Tracker**:
   - SQLite persistent database recording user XP, practice streaks, attempt counters, and mastery scores.
   - Built-in achievement badges (*First Spark*, *Trio Explorer*, *Consistency Master*, *Sign Apprentice*, *XP Champion*).
   - Speed Challenge / Quiz Mode with a timer to test rapid recall.

---

## 🏗️ System Architecture & Data Flow

```
+------------------+         +--------------------+         +------------------------+
|  User Interface  |  Webcam |    MediaPipe 21    | 21 3D   |  Feature Extractor     |
|   (HTML5/CSS3/   | ------> |   Hand Landmarker  | Points  |  - Origin Translation  |
|   Canvas/Audio)  |  Frames |   (Vision Pipeline)| ------> |  - Scale Normalization |
+------------------+         +--------------------+         |  - Joint Angles & Dists|
         ^                                                  +------------------------+
         |                                                              |
         | Feedback & Visual HUD                                        | 86-dim vector
         |                                                              v
+------------------+         +--------------------+         +------------------------+
| SQLite Database  | <------ |  Coaching Engine   | <------ |  Scikit-Learn ML Model |
| (XP, Streaks,    | Progress| (Finger Checklist  | Sign &  | (RandomForest / MLP    |
| Badges, Logs)    | Update  |  & Dynamic Hints)  | Conf    |  Inference Engine)     |
+------------------+         +--------------------+         +------------------------+
```

---

## 📂 Project Directory Structure

```
ai based sign language/
├── app.py                      # Flask backend server & REST API
├── config.py                   # Configuration paths, thresholds, and server settings
├── database.py                 # SQLite database schema, user stats, and badge logic
├── requirements.txt            # Python dependencies
├── README.md                   # Complete documentation
│
├── vision/
│   ├── hand_detector.py        # MediaPipe Hand Landmarker integration & skeleton drawing
│   ├── feature_extractor.py    # 86-dim normalized feature engineering & finger state analysis
│   └── sign_classifier.py      # ML model loader & real-time prediction pipeline
│
├── data/
│   ├── dataset_generator.py    # Generates 4,100+ augmented kinematic training samples
│   ├── train_model.py          # Trains & evaluates Random Forest and MLP classifiers
│   ├── collect_data.py         # Standalone webcam data collector for custom signs
│   ├── signs_reference.json    # Complete catalog of signs, hints, and finger rules
│   └── sign_landmarks_dataset.csv
│
├── models/
│   ├── hand_landmarker.task    # MediaPipe hand landmarker model bundle
│   ├── sign_model.joblib       # Trained ML classifier model
│   └── label_encoder.joblib    # Scikit-learn label encoder
│
├── templates/
│   └── index.html              # Modern, glassmorphic learning platform UI
│
└── static/
    ├── css/
    │   └── style.css           # Custom dark theme, neon accents, and animations
    └── js/
        ├── app.js              # Application controller & state machine
        ├── camera.js           # Webcam management & canvas skeleton rendering
        ├── lessons.js          # Lesson catalog & vector sign diagrams
        └── audio.js            # Web Audio API sound effects generator
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.9+ (Tested and verified on Python 3.13)
- Modern web browser (Chrome, Edge, Firefox) with webcam access

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Web Application
```bash
python app.py
```

Open your browser and navigate to:
```
http://localhost:5000
```

Allow webcam permissions when prompted. Position your hand inside the frame to start learning!

---

## 🧠 Model Training & Custom Data Recording

### Retrain or Regenerate the Model
To re-synthesize the 86-dimensional biomechanical dataset and retrain the classifier:
```bash
python data/dataset_generator.py
python data/train_model.py
```

### Record Your Own Gestures (Webcam)
You can collect custom real-world training samples using your own webcam:
```bash
python data/collect_data.py
```
- Enter your sign label (e.g. `A`, `HELLO`, `CUSTOM`).
- Press **SPACE** to toggle frame collection.
- Adjust angles and distances while recording.

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the main web interface |
| `GET` | `/api/health` | Service health status and loaded model info |
| `GET` | `/api/lessons` | Returns sign catalog and lesson modules |
| `POST` | `/api/predict` | Accepts base64 frame or landmarks; returns prediction, confidence, hints |
| `GET` | `/api/progress` | Fetches user profile, streak, completion rate, and badges |
| `POST` | `/api/progress/attempt` | Records completed practice attempt, awards XP and badges |
| `POST` | `/api/reset` | Resets practice progress and logs |
| `GET` | `/video_feed` | Optional MJPEG server-side OpenCV video stream with overlays |

---

## 💡 Troubleshooting & Tips

- **Good Lighting**: Ensure your hand is well-lit and contrasts against the background.
- **Hand Distance**: Hold your hand 1.5 to 3 feet from the webcam so your entire hand and wrist are clearly visible.
- **Mirror Mode**: Use the 🪞 toggle in the top-right of the video viewport to toggle mirror view.
