import csv
import numpy as np
import joblib
import sys
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report, accuracy_score

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DATASET_CSV_PATH, SIGN_MODEL_PATH, LABEL_ENCODER_PATH, MODELS_DIR

def load_dataset(csv_path):
    """Loads feature matrix X and label vector y from CSV."""
    X = []
    y = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            if not row:
                continue
            feats = [float(val) for val in row[:-1]]
            label = row[-1]
            X.append(feats)
            y.append(label)
    return np.array(X, dtype=np.float32), np.array(y)

def train_and_evaluate():
    """Trains machine learning classifiers, evaluates accuracy, and exports joblib assets."""
    print(f"Loading training data from {DATASET_CSV_PATH}...")
    X, y_raw = load_dataset(DATASET_CSV_PATH)
    print(f"Loaded {len(X)} samples with {X.shape[1]} features.")

    # Encode labels
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)
    class_names = list(label_encoder.classes_)
    print(f"Classes ({len(class_names)}): {class_names}")

    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"\nTraining Random Forest Classifier (150 trees)...")
    rf_model = RandomForestClassifier(
        n_estimators=150,
        max_depth=22,
        min_samples_split=2,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    rf_pred = rf_model.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_pred)
    print(f"Random Forest Test Accuracy: {rf_acc * 100:.2f}%")

    print(f"\nTraining Multi-Layer Perceptron (Neural Network)...")
    mlp_model = MLPClassifier(
        hidden_layer_sizes=(128, 64),
        max_iter=300,
        activation="relu",
        random_state=42,
        early_stopping=True
    )
    mlp_model.fit(X_train, y_train)
    mlp_pred = mlp_model.predict(X_test)
    mlp_acc = accuracy_score(y_test, mlp_pred)
    print(f"MLP Neural Network Test Accuracy: {mlp_acc * 100:.2f}%")

    # Select best model
    if rf_acc >= mlp_acc:
        best_model = rf_model
        best_name = "Random Forest"
        best_pred = rf_pred
    else:
        best_model = mlp_model
        best_name = "MLP Neural Network"
        best_pred = mlp_pred

    print(f"\nBest Model Selected: {best_name}")
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, best_pred, target_names=class_names, digits=3))

    # Save models
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, SIGN_MODEL_PATH)
    joblib.dump(label_encoder, LABEL_ENCODER_PATH)

    print(f"\nSuccessfully exported trained model to: {SIGN_MODEL_PATH}")
    print(f"Successfully exported label encoder to: {LABEL_ENCODER_PATH}")

    return best_model, label_encoder

if __name__ == "__main__":
    train_and_evaluate()
