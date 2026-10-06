import math
import numpy as np

def euclidean_dist(p1, p2):
    """Calculates 3D Euclidean distance between two landmark points."""
    return math.sqrt(
        (p1["x"] - p2["x"]) ** 2 +
        (p1["y"] - p2["y"]) ** 2 +
        (p1["z"] - p2["z"]) ** 2
    )

def angle_between_points(a, b, c):
    """
    Computes angle (in degrees) at joint b formed by points a-b-c.
    Useful for calculating finger bend / flexion.
    """
    v1 = np.array([a["x"] - b["x"], a["y"] - b["y"], a["z"] - b["z"]])
    v2 = np.array([c["x"] - b["x"], c["y"] - b["y"], c["z"] - b["z"]])
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    cosine = np.dot(v1, v2) / (norm1 * norm2)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))

class FeatureExtractor:
    """
    Extracts scale- and position-invariant feature vectors from 21 MediaPipe hand landmarks.
    Also provides granular anatomical finger status analysis for real-time user coaching.
    """

    def __init__(self):
        # Landmark indices
        self.WRIST = 0
        self.THUMB_CMC, self.THUMB_MCP, self.THUMB_IP, self.THUMB_TIP = 1, 2, 3, 4
        self.INDEX_MCP, self.INDEX_PIP, self.INDEX_DIP, self.INDEX_TIP = 5, 6, 7, 8
        self.MIDDLE_MCP, self.MIDDLE_PIP, self.MIDDLE_DIP, self.MIDDLE_TIP = 9, 10, 11, 12
        self.RING_MCP, self.RING_PIP, self.RING_DIP, self.RING_TIP = 13, 14, 15, 16
        self.PINKY_MCP, self.PINKY_PIP, self.PINKY_DIP, self.PINKY_TIP = 17, 18, 19, 20

    def extract_features(self, landmarks):
        """
        Extracts an 80+ dimension invariant feature vector from 21 landmarks.
        Components:
        1. 63 translated and scale-normalized coordinates (relative to wrist)
        2. 5 fingertip-to-wrist normalized distances
        3. 8 pairwise fingertip distances
        4. 4 finger PIP flexion angles (degrees)
        5. 5 extension state ratios
        """
        if not landmarks or len(landmarks) < 21:
            return None

        wrist = landmarks[self.WRIST]

        # 1. Scale factor: distance from wrist to middle MCP joint
        scale = euclidean_dist(wrist, landmarks[self.MIDDLE_MCP])
        if scale < 1e-4:
            # Fallback to max span
            dists = [euclidean_dist(wrist, lm) for lm in landmarks]
            scale = max(dists) if max(dists) > 1e-4 else 1.0

        # 2. Normalized coordinates (63 values)
        norm_coords = []
        for lm in landmarks:
            norm_coords.extend([
                (lm["x"] - wrist["x"]) / scale,
                (lm["y"] - wrist["y"]) / scale,
                (lm["z"] - wrist["z"]) / scale
            ])

        # 3. Fingertip to wrist distances (normalized)
        tip_indices = [self.THUMB_TIP, self.INDEX_TIP, self.MIDDLE_TIP, self.RING_TIP, self.PINKY_TIP]
        tip_wrist_dists = [euclidean_dist(landmarks[idx], wrist) / scale for idx in tip_indices]

        # 4. Pairwise fingertip distances (normalized)
        pairwise_dists = [
            euclidean_dist(landmarks[self.THUMB_TIP], landmarks[self.INDEX_TIP]) / scale,
            euclidean_dist(landmarks[self.THUMB_TIP], landmarks[self.MIDDLE_TIP]) / scale,
            euclidean_dist(landmarks[self.THUMB_TIP], landmarks[self.RING_TIP]) / scale,
            euclidean_dist(landmarks[self.THUMB_TIP], landmarks[self.PINKY_TIP]) / scale,
            euclidean_dist(landmarks[self.INDEX_TIP], landmarks[self.MIDDLE_TIP]) / scale,
            euclidean_dist(landmarks[self.MIDDLE_TIP], landmarks[self.RING_TIP]) / scale,
            euclidean_dist(landmarks[self.RING_TIP], landmarks[self.PINKY_TIP]) / scale,
            euclidean_dist(landmarks[self.INDEX_TIP], landmarks[self.PINKY_TIP]) / scale
        ]

        # 5. Joint angles (flexion)
        angles = [
            angle_between_points(landmarks[self.THUMB_MCP], landmarks[self.THUMB_IP], landmarks[self.THUMB_TIP]),
            angle_between_points(landmarks[self.INDEX_MCP], landmarks[self.INDEX_PIP], landmarks[self.INDEX_TIP]),
            angle_between_points(landmarks[self.MIDDLE_MCP], landmarks[self.MIDDLE_PIP], landmarks[self.MIDDLE_TIP]),
            angle_between_points(landmarks[self.RING_MCP], landmarks[self.RING_PIP], landmarks[self.RING_TIP]),
            angle_between_points(landmarks[self.PINKY_MCP], landmarks[self.PINKY_PIP], landmarks[self.PINKY_TIP])
        ]

        # 6. Finger extension ratios (tip-to-wrist / mcp-to-wrist)
        extension_ratios = [
            euclidean_dist(landmarks[self.INDEX_TIP], wrist) / (euclidean_dist(landmarks[self.INDEX_MCP], wrist) + 1e-4),
            euclidean_dist(landmarks[self.MIDDLE_TIP], wrist) / (euclidean_dist(landmarks[self.MIDDLE_MCP], wrist) + 1e-4),
            euclidean_dist(landmarks[self.RING_TIP], wrist) / (euclidean_dist(landmarks[self.RING_MCP], wrist) + 1e-4),
            euclidean_dist(landmarks[self.PINKY_TIP], wrist) / (euclidean_dist(landmarks[self.PINKY_MCP], wrist) + 1e-4),
            euclidean_dist(landmarks[self.THUMB_TIP], landmarks[self.INDEX_MCP]) / scale
        ]

        # Combine all features into single 1D feature array (63 + 5 + 8 + 5 + 5 = 86 features)
        features = np.array(norm_coords + tip_wrist_dists + pairwise_dists + angles + extension_ratios, dtype=np.float32)
        return features

    def analyze_finger_states(self, landmarks):
        """
        Determines the anatomical state (extended, curled, curved, tucked) for each finger.
        Returns a dictionary with state breakdown and boolean flags.
        """
        if not landmarks or len(landmarks) < 21:
            return {}

        wrist = landmarks[self.WRIST]
        states = {}

        # Index
        index_mcp_dist = euclidean_dist(landmarks[self.INDEX_MCP], wrist)
        index_pip_dist = euclidean_dist(landmarks[self.INDEX_PIP], wrist)
        index_tip_dist = euclidean_dist(landmarks[self.INDEX_TIP], wrist)
        index_angle = angle_between_points(landmarks[self.INDEX_MCP], landmarks[self.INDEX_PIP], landmarks[self.INDEX_TIP])
        is_index_ext = index_tip_dist > index_pip_dist and index_angle > 140
        states["index"] = "extended" if is_index_ext else ("curled" if index_angle < 100 else "curved")

        # Middle
        mid_pip_dist = euclidean_dist(landmarks[self.MIDDLE_PIP], wrist)
        mid_tip_dist = euclidean_dist(landmarks[self.MIDDLE_TIP], wrist)
        mid_angle = angle_between_points(landmarks[self.MIDDLE_MCP], landmarks[self.MIDDLE_PIP], landmarks[self.MIDDLE_TIP])
        is_mid_ext = mid_tip_dist > mid_pip_dist and mid_angle > 140
        states["middle"] = "extended" if is_mid_ext else ("curled" if mid_angle < 100 else "curved")

        # Ring
        ring_pip_dist = euclidean_dist(landmarks[self.RING_PIP], wrist)
        ring_tip_dist = euclidean_dist(landmarks[self.RING_TIP], wrist)
        ring_angle = angle_between_points(landmarks[self.RING_MCP], landmarks[self.RING_PIP], landmarks[self.RING_TIP])
        is_ring_ext = ring_tip_dist > ring_pip_dist and ring_angle > 140
        states["ring"] = "extended" if is_ring_ext else ("curled" if ring_angle < 100 else "curved")

        # Pinky
        pinky_pip_dist = euclidean_dist(landmarks[self.PINKY_PIP], wrist)
        pinky_tip_dist = euclidean_dist(landmarks[self.PINKY_TIP], wrist)
        pinky_angle = angle_between_points(landmarks[self.PINKY_MCP], landmarks[self.PINKY_PIP], landmarks[self.PINKY_TIP])
        is_pinky_ext = pinky_tip_dist > pinky_pip_dist and pinky_angle > 140
        states["pinky"] = "extended" if is_pinky_ext else ("curled" if pinky_angle < 100 else "curved")

        # Thumb
        thumb_tip = landmarks[self.THUMB_TIP]
        pinky_mcp = landmarks[self.PINKY_MCP]
        thumb_pinky_dist = euclidean_dist(thumb_tip, pinky_mcp)
        thumb_index_dist = euclidean_dist(thumb_tip, landmarks[self.INDEX_MCP])
        thumb_angle = angle_between_points(landmarks[self.THUMB_MCP], landmarks[self.THUMB_IP], landmarks[self.THUMB_TIP])

        if thumb_pinky_dist < 0.18:
            states["thumb"] = "folded_across_palm"
        elif thumb_index_dist < 0.12:
            states["thumb"] = "touching_index"
        elif thumb_angle > 140 and thumb_index_dist > 0.25:
            states["thumb"] = "extended"
        else:
            states["thumb"] = "neutral"

        # Special metrics
        states["index_middle_spread"] = euclidean_dist(landmarks[self.INDEX_TIP], landmarks[self.MIDDLE_TIP]) > 0.12
        states["thumb_index_touching"] = euclidean_dist(landmarks[self.THUMB_TIP], landmarks[self.INDEX_TIP]) < 0.08

        return states

    def generate_coaching_hints(self, target_sign_code, landmarks, signs_catalog=None):
        """
        Generates actionable, finger-specific feedback when user's hand deviates from the target sign.
        """
        if not landmarks or len(landmarks) < 21:
            return ["No hand clearly detected in frame. Bring your hand into the camera view."]

        states = self.analyze_finger_states(landmarks)
        hints = []

        if target_sign_code == "A":
            if states.get("index") != "curled" or states.get("middle") != "curled":
                hints.append("Curl all four fingers into a tight fist.")
            if states.get("thumb") == "folded_across_palm":
                hints.append("Keep your thumb upright against the outer edge of your index finger, not across your palm.")

        elif target_sign_code == "B":
            if states.get("index") != "extended" or states.get("middle") != "extended" or states.get("ring") != "extended" or states.get("pinky") != "extended":
                hints.append("Straighten all 4 fingers upward.")
            if states.get("thumb") != "folded_across_palm":
                hints.append("Fold your thumb flat across your palm.")

        elif target_sign_code == "C":
            if any(states.get(f) == "extended" for f in ["index", "middle", "ring", "pinky"]):
                hints.append("Curve all four fingers into a gentle C-shape arc.")

        elif target_sign_code == "D":
            if states.get("index") != "extended":
                hints.append("Point your index finger straight up.")
            if states.get("middle") == "extended" or states.get("ring") == "extended":
                hints.append("Curl your middle, ring, and pinky down to meet your thumb tip.")

        elif target_sign_code == "F":
            if not states.get("thumb_index_touching"):
                hints.append("Touch your thumb and index tips together to make an 'OK' circle.")
            if states.get("pinky") != "extended" or states.get("ring") != "extended":
                hints.append("Keep your middle, ring, and pinky fingers upright and spread.")

        elif target_sign_code == "I":
            if states.get("pinky") != "extended":
                hints.append("Extend only your pinky finger straight up.")
            if states.get("index") != "curled" or states.get("middle") != "curled":
                hints.append("Curl your other fingers completely into a fist.")

        elif target_sign_code in ["L"]:
            if states.get("index") != "extended":
                hints.append("Point your index finger straight up.")
            if states.get("thumb") != "extended":
                hints.append("Extend your thumb out horizontally to form a 90-degree 'L'.")

        elif target_sign_code in ["V", "PEACE"]:
            if states.get("index") != "extended" or states.get("middle") != "extended":
                hints.append("Extend both your index and middle fingers straight up.")
            elif not states.get("index_middle_spread"):
                hints.append("Spread your index and middle fingers apart into a 'V'.")
            if states.get("ring") != "curled" or states.get("pinky") != "curled":
                hints.append("Curl your ring and pinky fingers down into your palm.")

        elif target_sign_code == "W":
            if states.get("index") != "extended" or states.get("middle") != "extended" or states.get("ring") != "extended":
                hints.append("Hold 3 fingers (index, middle, ring) upright and spread apart.")
            if states.get("pinky") != "curled":
                hints.append("Hold down your pinky finger with your thumb.")

        elif target_sign_code == "Y":
            if states.get("thumb") != "extended" or states.get("pinky") != "extended":
                hints.append("Stick both your thumb and pinky out ('shaka' sign).")
            if states.get("middle") != "curled":
                hints.append("Curl your index, middle, and ring fingers tightly down.")

        elif target_sign_code == "I_LOVE_YOU":
            if states.get("thumb") != "extended" or states.get("index") != "extended" or states.get("pinky") != "extended":
                hints.append("Extend your thumb, index finger, and pinky finger simultaneously.")
            if states.get("middle") != "curled" or states.get("ring") != "curled":
                hints.append("Keep your middle and ring fingers curled firmly into your palm.")

        if not hints:
            hints.append("Hand posture looks great! Hold steady to confirm.")

        return hints
