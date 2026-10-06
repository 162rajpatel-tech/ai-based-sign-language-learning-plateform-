import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from config import DB_PATH, SIGNS_REFERENCE_PATH

def get_connection():
    """Get a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables and populates baseline lessons and badges."""
    conn = get_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        total_xp INTEGER DEFAULT 0,
        streak_days INTEGER DEFAULT 0,
        last_active_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Lessons Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sign_code TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        description TEXT,
        hints TEXT,
        finger_rules TEXT
    );
    """)

    # User Sign Progress Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        sign_code TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        successes INTEGER DEFAULT 0,
        best_confidence REAL DEFAULT 0.0,
        mastery_score REAL DEFAULT 0.0,
        completed INTEGER DEFAULT 0,
        last_practiced TIMESTAMP,
        UNIQUE(user_id, sign_code),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Practice Session Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS practice_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        sign_code TEXT NOT NULL,
        predicted_sign TEXT NOT NULL,
        confidence REAL NOT NULL,
        is_correct INTEGER NOT NULL,
        duration_ms INTEGER DEFAULT 0,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Badges Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        badge_key TEXT NOT NULL,
        badge_title TEXT NOT NULL,
        badge_desc TEXT NOT NULL,
        icon TEXT NOT NULL,
        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, badge_key),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    conn.commit()

    # Populate lessons from signs_reference.json if empty
    cursor.execute("SELECT COUNT(*) as count FROM lessons;")
    if cursor.fetchone()["count"] == 0 and SIGNS_REFERENCE_PATH.exists():
        with open(SIGNS_REFERENCE_PATH, "r", encoding="utf-8") as f:
            signs_data = json.load(f)
        for code, info in signs_data.items():
            cursor.execute("""
            INSERT OR IGNORE INTO lessons (sign_code, category, name, difficulty, description, hints, finger_rules)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                code,
                info.get("category", "alphabet"),
                info.get("name", code),
                info.get("difficulty", "Beginner"),
                info.get("description", ""),
                json.dumps(info.get("hints", [])),
                json.dumps(info.get("finger_rules", {}))
            ))
        conn.commit()

    # Create default user if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'Learner';")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, total_xp, streak_days, last_active_date) VALUES ('Learner', 0, 1, ?);", (str(date.today()),))
        conn.commit()

    conn.close()

def get_or_create_user(username="Learner"):
    """Fetch existing user or create a new user profile."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?;", (username,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (username, total_xp, streak_days, last_active_date) VALUES (?, 0, 1, ?);", (username, str(date.today())))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE username = ?;", (username,))
        user = cursor.fetchone()
    user_dict = dict(user)
    conn.close()
    return user_dict

def update_user_streak(cursor, user_id):
    """Updates the user practice streak counter based on activity date."""
    cursor.execute("SELECT last_active_date, streak_days FROM users WHERE id = ?;", (user_id,))
    row = cursor.fetchone()
    if not row:
        return 1
    
    today_str = str(date.today())
    last_active = row["last_active_date"]
    streak = row["streak_days"] or 0

    if last_active == today_str:
        return streak
    
    if last_active:
        last_date = datetime.strptime(last_active, "%Y-%m-%d").date()
        diff = (date.today() - last_date).days
        if diff == 1:
            streak += 1
        elif diff > 1:
            streak = 1
    else:
        streak = 1

    cursor.execute("UPDATE users SET streak_days = ?, last_active_date = ? WHERE id = ?;", (streak, today_str, user_id))
    return streak

def record_practice_attempt(user_id, sign_code, predicted_sign, confidence, is_correct, duration_ms=0):
    """Logs an attempt, computes earned XP, updates mastery score, and checks for unlockable badges."""
    conn = get_connection()
    cursor = conn.cursor()

    # Log practice attempt
    cursor.execute("""
    INSERT INTO practice_logs (user_id, sign_code, predicted_sign, confidence, is_correct, duration_ms)
    VALUES (?, ?, ?, ?, ?, ?);
    """, (user_id, sign_code, predicted_sign, confidence, 1 if is_correct else 0, duration_ms))

    # Update streak
    streak = update_user_streak(cursor, user_id)

    # Calculate XP
    earned_xp = 0
    if is_correct:
        # 25 base XP for correct match + bonus up to 15 for high confidence
        earned_xp = 25 + int(confidence * 15)
    else:
        earned_xp = 5  # Participation XP

    # Update or insert user_progress
    cursor.execute("SELECT * FROM user_progress WHERE user_id = ? AND sign_code = ?;", (user_id, sign_code))
    progress = cursor.fetchone()

    if progress:
        attempts = progress["attempts"] + 1
        successes = progress["successes"] + (1 if is_correct else 0)
        best_conf = max(progress["best_confidence"], confidence if is_correct else 0.0)
        # Mastery calculation based on success ratio and best confidence
        success_ratio = successes / attempts
        mastery = min(100.0, round((success_ratio * 0.6 + (best_conf) * 0.4) * 100, 1))
        completed = 1 if mastery >= 75.0 else 0

        cursor.execute("""
        UPDATE user_progress
        SET attempts = ?, successes = ?, best_confidence = ?, mastery_score = ?, completed = ?, last_practiced = CURRENT_TIMESTAMP
        WHERE user_id = ? AND sign_code = ?;
        """, (attempts, successes, best_conf, mastery, completed, user_id, sign_code))
    else:
        attempts = 1
        successes = 1 if is_correct else 0
        best_conf = confidence if is_correct else 0.0
        mastery = 80.0 if is_correct else 10.0
        completed = 1 if mastery >= 75.0 else 0

        cursor.execute("""
        INSERT INTO user_progress (user_id, sign_code, attempts, successes, best_confidence, mastery_score, completed, last_practiced)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, (user_id, sign_code, attempts, successes, best_conf, mastery, completed))

    # Increment total XP in users
    cursor.execute("UPDATE users SET total_xp = total_xp + ? WHERE id = ?;", (earned_xp, user_id))

    # Check and award badges
    new_badges = check_and_award_badges(cursor, user_id)

    conn.commit()
    conn.close()

    return {
        "earned_xp": earned_xp,
        "is_correct": is_correct,
        "streak": streak,
        "new_badges": new_badges
    }

def check_and_award_badges(cursor, user_id):
    """Checks conditions and unlocks new achievement badges."""
    newly_unlocked = []

    # Get user metrics
    cursor.execute("SELECT total_xp, streak_days FROM users WHERE id = ?;", (user_id,))
    user_row = cursor.fetchone()
    total_xp = user_row["total_xp"] if user_row else 0
    streak = user_row["streak_days"] if user_row else 0

    cursor.execute("SELECT COUNT(*) as count FROM user_progress WHERE user_id = ? AND successes > 0;", (user_id,))
    distinct_signs = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM user_progress WHERE user_id = ? AND completed = 1;", (user_id,))
    mastered_signs = cursor.fetchone()["count"]

    potential_badges = [
        ("first_sign", "First Spark", "Successfully performed your very first sign!", "✨", distinct_signs >= 1),
        ("three_signs", "Trio Explorer", "Learned and completed 3 different signs!", "🎯", distinct_signs >= 3),
        ("streak_3", "Consistency Master", "Maintained a 3-day practice streak!", "🔥", streak >= 3),
        ("alphabet_novice", "Sign Apprentice", "Mastered at least 5 signs with 75%+ accuracy!", "🏅", mastered_signs >= 5),
        ("xp_500", "XP Champion", "Accumulated 500 total XP points!", "⚡", total_xp >= 500)
    ]

    for key, title, desc, icon, condition in potential_badges:
        if condition:
            cursor.execute("SELECT id FROM badges WHERE user_id = ? AND badge_key = ?;", (user_id, key))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO badges (user_id, badge_key, badge_title, badge_desc, icon)
                VALUES (?, ?, ?, ?, ?);
                """, (user_id, key, title, desc, icon))
                newly_unlocked.append({"key": key, "title": title, "desc": desc, "icon": icon})

    return newly_unlocked

def get_user_stats(user_id=1):
    """Fetches user overview, progress summary, and unlocked badges."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return None
    user_data = dict(user)

    cursor.execute("""
    SELECT p.*, l.name, l.category, l.difficulty
    FROM user_progress p
    JOIN lessons l ON p.sign_code = l.sign_code
    WHERE p.user_id = ?
    ORDER BY p.last_practiced DESC;
    """, (user_id,))
    progress_list = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM badges WHERE user_id = ? ORDER BY unlocked_at DESC;", (user_id,))
    badges = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) as total FROM lessons;")
    total_lessons = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as completed FROM user_progress WHERE user_id = ? AND completed = 1;", (user_id,))
    completed_lessons = cursor.fetchone()["completed"]

    conn.close()

    return {
        "user": user_data,
        "progress": progress_list,
        "badges": badges,
        "stats": {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "completion_rate": round((completed_lessons / total_lessons * 100), 1) if total_lessons > 0 else 0
        }
    }

def reset_user_stats(user_id=1):
    """Resets progress and XP for user testing and rehearsal."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET total_xp = 0, streak_days = 1, last_active_date = ? WHERE id = ?;", (str(date.today()), user_id))
    cursor.execute("DELETE FROM user_progress WHERE user_id = ?;", (user_id,))
    cursor.execute("DELETE FROM practice_logs WHERE user_id = ?;", (user_id,))
    cursor.execute("DELETE FROM badges WHERE user_id = ?;", (user_id,))
    conn.commit()
    conn.close()
    return True
