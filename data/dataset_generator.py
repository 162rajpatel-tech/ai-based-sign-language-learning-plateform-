import numpy as np
import csv
import json
import math
import os
from pathlib import Path
import sys

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from vision.feature_extractor import FeatureExtractor
from config import DATA_DIR, DATASET_CSV_PATH

def rotate_3d(points, yaw_deg, pitch_deg, roll_deg):
    """Rotates 21 landmark 3D points around the wrist (landmark 0)."""
    yaw = np.radians(yaw_deg)
    pitch = np.radians(pitch_deg)
    roll = np.radians(roll_deg)

    # Rotation matrices
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(pitch), -np.sin(pitch)],
        [0, np.sin(pitch), np.cos(pitch)]
    ])
    Ry = np.array([
        [np.cos(yaw), 0, np.sin(yaw)],
        [0, 1, 0],
        [-np.sin(yaw), 0, np.cos(yaw)]
    ])
    Rz = np.array([
        [np.cos(roll), -np.sin(roll), 0],
        [np.sin(roll), np.cos(roll), 0],
        [0, 0, 1]
    ])
    R = Rz @ Ry @ Rx

    origin = points[0].copy()
    shifted = points - origin
    rotated = (R @ shifted.T).T + origin
    return rotated

def get_base_hand_kinematics():
    """
    Returns an anatomically proportioned base neutral hand model in 3D coordinates.
    Wrist is at (0.50, 0.75, 0.0).
    """
    hand = np.zeros((21, 3), dtype=np.float32)
    # 0: Wrist
    hand[0] = [0.50, 0.75, 0.0]

    # Thumb: 1: CMC, 2: MCP, 3: IP, 4: TIP
    hand[1] = [0.44, 0.70, -0.01]
    hand[2] = [0.40, 0.64, -0.02]
    hand[3] = [0.38, 0.58, -0.03]
    hand[4] = [0.36, 0.52, -0.04]

    # Index: 5: MCP, 6: PIP, 7: DIP, 8: TIP
    hand[5] = [0.45, 0.57, 0.0]
    hand[6] = [0.44, 0.47, 0.0]
    hand[7] = [0.43, 0.40, 0.0]
    hand[8] = [0.42, 0.33, 0.0]

    # Middle: 9: MCP, 10: PIP, 11: DIP, 12: TIP
    hand[9] = [0.50, 0.56, 0.0]
    hand[10] = [0.50, 0.45, 0.0]
    hand[11] = [0.50, 0.38, 0.0]
    hand[12] = [0.50, 0.30, 0.0]

    # Ring: 13: MCP, 14: PIP, 15: DIP, 16: TIP
    hand[13] = [0.55, 0.57, 0.0]
    hand[14] = [0.56, 0.47, 0.0]
    hand[15] = [0.57, 0.40, 0.0]
    hand[16] = [0.58, 0.34, 0.0]

    # Pinky: 17: MCP, 18: PIP, 19: DIP, 20: TIP
    hand[17] = [0.60, 0.60, 0.0]
    hand[18] = [0.62, 0.52, 0.0]
    hand[19] = [0.63, 0.46, 0.0]
    hand[20] = [0.64, 0.40, 0.0]

    return hand

def synthesize_canonical_pose(word_code):
    """
    Constructs an anatomically accurate canonical 21-point 3D pose for meaningful words.
    """
    hand = get_base_hand_kinematics()

    def curl_finger(mcp_idx, pip_idx, dip_idx, tip_idx, forward_z=0.04):
        base_mcp = hand[mcp_idx]
        hand[pip_idx] = base_mcp + [-0.01, -0.05, forward_z]
        hand[dip_idx] = base_mcp + [0.0, -0.01, forward_z * 1.5]
        hand[tip_idx] = base_mcp + [0.01, 0.03, forward_z]

    def curve_finger(mcp_idx, pip_idx, dip_idx, tip_idx):
        base_mcp = hand[mcp_idx]
        hand[pip_idx] = base_mcp + [-0.02, -0.07, 0.03]
        hand[dip_idx] = base_mcp + [-0.04, -0.04, 0.04]
        hand[tip_idx] = base_mcp + [-0.06, -0.02, 0.05]

    if word_code == "HELLO":
        # Open flat hand salute near temple
        hand[4] = [0.38, 0.50, -0.02]
        hand[8] = [0.44, 0.32, 0.0]
        hand[12] = [0.49, 0.30, 0.0]
        hand[16] = [0.54, 0.32, 0.0]
        hand[20] = [0.59, 0.37, 0.0]

    elif word_code == "THANK_YOU":
        # Flat hand from chin moving slightly forward
        hand[4] = [0.41, 0.54, 0.03]
        hand[8] = [0.45, 0.36, 0.04]
        hand[12] = [0.50, 0.34, 0.04]
        hand[16] = [0.55, 0.36, 0.04]
        hand[20] = [0.60, 0.40, 0.04]

    elif word_code == "YES":
        # S-fist dipping forward
        curl_finger(5, 6, 7, 8)
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        hand[4] = [0.46, 0.58, 0.04] # Thumb curled over fingers

    elif word_code == "NO":
        # Index and middle closing onto thumb tip
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        hand[4] = [0.45, 0.53, 0.04]
        hand[8] = [0.45, 0.53, 0.04]
        hand[12] = [0.46, 0.53, 0.04]

    elif word_code == "PLEASE":
        # Flat open hand over chest
        hand[4] = [0.40, 0.56, 0.02]
        hand[8] = [0.45, 0.34, 0.01]
        hand[12] = [0.50, 0.32, 0.01]
        hand[16] = [0.55, 0.34, 0.01]
        hand[20] = [0.60, 0.39, 0.01]

    elif word_code == "SORRY":
        # Closed fist against chest
        curl_finger(5, 6, 7, 8)
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        hand[1] = [0.44, 0.70, 0.02]
        hand[2] = [0.47, 0.65, 0.03]
        hand[3] = [0.50, 0.63, 0.04]
        hand[4] = [0.53, 0.62, 0.04] # Thumb across fingers

    elif word_code == "HELP":
        # Thumbs up gesture (dominant hand lifting)
        curl_finger(5, 6, 7, 8)
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        hand[1] = [0.44, 0.68, 0.0]
        hand[2] = [0.42, 0.60, 0.0]
        hand[3] = [0.40, 0.52, 0.0]
        hand[4] = [0.38, 0.44, 0.0] # Thumb pointing straight up!

    elif word_code == "I_LOVE_YOU":
        # Thumb, Index, Pinky extended; Middle and Ring curled
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        hand[1] = [0.43, 0.70, 0.0]
        hand[2] = [0.37, 0.67, 0.0]
        hand[3] = [0.31, 0.64, 0.0]
        hand[4] = [0.25, 0.61, 0.0] # Thumb out
        hand[8] = [0.42, 0.33, 0.0] # Index up
        hand[20] = [0.68, 0.37, 0.0] # Pinky up

    elif word_code == "GOOD":
        # Open hand chin to palm
        hand[4] = [0.42, 0.52, 0.02]
        hand[8] = [0.45, 0.34, 0.02]
        hand[12] = [0.50, 0.32, 0.02]
        hand[16] = [0.55, 0.34, 0.02]
        hand[20] = [0.60, 0.38, 0.02]

    elif word_code == "STOP":
        # Vertical chop flat hand
        hand[4] = [0.42, 0.52, 0.0]
        hand[8] = [0.45, 0.33, 0.0]
        hand[12] = [0.50, 0.31, 0.0]
        hand[16] = [0.55, 0.33, 0.0]
        hand[20] = [0.60, 0.37, 0.0]

    elif word_code == "OK":
        # OK circle (thumb + index touch; 3 fingers up)
        hand[8] = [0.42, 0.53, 0.03]
        hand[4] = [0.42, 0.53, 0.03] # Touching
        hand[7] = [0.43, 0.49, 0.02]
        hand[6] = [0.44, 0.52, 0.01]

    elif word_code == "PEACE":
        # V-sign (Index and middle spread up, others curled)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        hand[6] = [0.42, 0.46, 0.0]
        hand[7] = [0.39, 0.39, 0.0]
        hand[8] = [0.36, 0.31, 0.0] # spread left
        hand[10] = [0.52, 0.46, 0.0]
        hand[11] = [0.55, 0.39, 0.0]
        hand[12] = [0.58, 0.31, 0.0] # spread right
        hand[4] = [0.48, 0.62, 0.03]

    elif word_code == "WELCOME":
        # Curved open hand welcoming inward
        curve_finger(5, 6, 7, 8)
        curve_finger(9, 10, 11, 12)
        curve_finger(13, 14, 15, 16)
        curve_finger(17, 18, 19, 20)
        hand[4] = [0.42, 0.56, 0.04]

    elif word_code == "CALL_ME":
        # Shaka phone to ear (thumb and pinky extended, middle 3 curled)
        curl_finger(5, 6, 7, 8)
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        hand[1] = [0.43, 0.70, 0.0]
        hand[2] = [0.37, 0.67, 0.0]
        hand[3] = [0.31, 0.64, 0.0]
        hand[4] = [0.25, 0.61, 0.0] # Thumb out
        hand[18] = [0.63, 0.52, 0.0]
        hand[19] = [0.67, 0.44, 0.0]
        hand[20] = [0.72, 0.36, 0.0] # Pinky out

    elif word_code == "WATER":
        # W-handshape (Index, Middle, Ring spread up; Pinky held by thumb)
        curl_finger(17, 18, 19, 20)
        hand[8] = [0.40, 0.32, 0.0]
        hand[12] = [0.50, 0.30, 0.0]
        hand[16] = [0.60, 0.33, 0.0]
        hand[4] = [0.56, 0.58, 0.03]

    return hand

def generate_augmented_dataset(samples_per_word=240):
    """
    Synthesizes rich training samples for meaningful words and gestures.
    """
    words = [
        "HELLO", "THANK_YOU", "YES", "NO", "PLEASE", 
        "SORRY", "HELP", "I_LOVE_YOU", "GOOD", "STOP", 
        "OK", "PEACE", "WELCOME", "CALL_ME", "WATER"
    ]

    extractor = FeatureExtractor()
    dataset_records = []

    print(f"Generating synthetic biomechanical dataset for {len(words)} meaningful words ({samples_per_word} samples/word)...")
    np.random.seed(42)

    for word in words:
        base_pose = synthesize_canonical_pose(word)

        for _ in range(samples_per_word):
            # 1. 3D Rotation variations
            yaw = np.random.uniform(-18.0, 18.0)
            pitch = np.random.uniform(-15.0, 15.0)
            roll = np.random.uniform(-15.0, 15.0)
            pose = rotate_3d(base_pose, yaw, pitch, roll)

            # 2. Scale variation
            scale_factor = np.random.uniform(0.80, 1.25)
            pose = (pose - pose[0]) * scale_factor + pose[0]

            # 3. Translation variation
            shift_x = np.random.uniform(-0.12, 0.12)
            shift_y = np.random.uniform(-0.12, 0.12)
            pose[:, 0] += shift_x
            pose[:, 1] += shift_y

            # 4. Joint jitter noise
            jitter = np.random.normal(0.0, 0.012, pose.shape).astype(np.float32)
            jitter[0] = 0.0 # Keep wrist stable
            pose = pose + jitter

            # Convert to landmark format
            landmarks = [{"x": float(p[0]), "y": float(p[1]), "z": float(p[2])} for p in pose]

            # Extract normalized feature vector
            feats = extractor.extract_features(landmarks)
            if feats is not None:
                record = list(feats)
                record.append(word)
                dataset_records.append(record)

    # Save to CSV using standard csv writer
    num_features = len(dataset_records[0]) - 1
    headers = [f"f_{i}" for i in range(num_features)] + ["label"]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATASET_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(dataset_records)

    print(f"Generated {len(dataset_records)} meaningful word samples with {num_features} features. Saved to {DATASET_CSV_PATH}")
    return dataset_records

if __name__ == "__main__":
    generate_augmented_dataset()
