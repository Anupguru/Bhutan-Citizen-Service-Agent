
import sqlite3
from pathlib import Path
from datetime import datetime


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "memory" / "agent_memory.db"


# ==========================================
# 1. DATABASE CONNECTION
# ==========================================

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ==========================================
# 2. INITIALIZE DATABASE
# ==========================================

def init_db():

    connection = get_connection()
    cursor = connection.cursor()

    # Store citizen interactions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            query TEXT NOT NULL,
            response TEXT,
            tools_used TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    # Store citizen feedback
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interaction_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (interaction_id)
                REFERENCES interactions(id)
        )
    """)

    connection.commit()
    connection.close()

    print("[DATABASE] Database initialized successfully.")


# ==========================================
# 3. SAVE CITIZEN INTERACTION
# ==========================================

def save_interaction(
    session_id,
    query,
    response,
    tools_used=None
):

    connection = get_connection()
    cursor = connection.cursor()

    tools_text = ", ".join(tools_used or [])

    cursor.execute("""
        INSERT INTO interactions
        (session_id, query, response, tools_used, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session_id,
        query,
        response,
        tools_text,
        datetime.now().isoformat()
    ))

    interaction_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return interaction_id


# ==========================================
# 4. SAVE CITIZEN FEEDBACK
# ==========================================

def save_feedback(
    interaction_id,
    rating,
    comment=""
):

    if isinstance(rating, bool) or rating not in [1, 2, 3, 4, 5]:
        raise ValueError("Rating must be between 1 and 5.")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO feedback
        (interaction_id, rating, comment, timestamp)
        VALUES (?, ?, ?, ?)
    """, (
        interaction_id,
        rating,
        comment.strip(),
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()

    print("[DATABASE] Citizen feedback saved successfully.")


# ==========================================
# 5. RETRIEVE RECENT CONVERSATIONS
# ==========================================

def get_recent_interactions(
    session_id,
    limit=5
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM interactions
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (session_id, limit))

    results = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return results


# ==========================================
# 6. RETRIEVE ALL INTERACTIONS
# ==========================================

def get_all_interactions():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM interactions
        ORDER BY id DESC
    """)

    results = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return results


# ==========================================
# 7. RETRIEVE CITIZEN FEEDBACK
# ==========================================

def get_feedback_records(limit=100):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            feedback.id AS feedback_id,
            feedback.interaction_id,
            feedback.rating,
            feedback.comment,
            feedback.timestamp AS feedback_timestamp,
            interactions.query,
            interactions.response,
            interactions.tools_used
        FROM feedback
        INNER JOIN interactions
            ON feedback.interaction_id = interactions.id
        ORDER BY feedback.id DESC
        LIMIT ?
    """, (limit,))

    results = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return results


# ==========================================
# 8. CALCULATE FEEDBACK STATISTICS
# ==========================================

def get_feedback_summary():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) AS total_feedback,
            AVG(rating) AS average_rating,

            SUM(
                CASE WHEN rating >= 4
                THEN 1 ELSE 0 END
            ) AS positive_feedback,

            SUM(
                CASE WHEN rating = 3
                THEN 1 ELSE 0 END
            ) AS neutral_feedback,

            SUM(
                CASE WHEN rating <= 2
                THEN 1 ELSE 0 END
            ) AS negative_feedback

        FROM feedback
    """)

    result = cursor.fetchone()

    connection.close()

    return {
        "total_feedback": result["total_feedback"] or 0,
        "average_rating": round(result["average_rating"] or 0, 2),
        "positive_feedback": result["positive_feedback"] or 0,
        "neutral_feedback": result["neutral_feedback"] or 0,
        "negative_feedback": result["negative_feedback"] or 0
    }


# ==========================================
# 9. GENERATE FEEDBACK-BASED ADAPTATION
# ==========================================

def get_adaptation_guidance():

    summary = get_feedback_summary()

    feedback_records = get_feedback_records(limit=100)

    total = summary["total_feedback"]

    # Do not adapt based on too little feedback.
    if total < 3:

        return {
            "adaptation_active": False,
            "reason": "Not enough feedback collected yet.",
            "guidance": (
                "Continue providing clear, simple and accurate "
                "government service guidance."
            ),
            "feedback_summary": summary
        }

    positive = summary["positive_feedback"]
    negative = summary["negative_feedback"]

    guidance = []

    # Identify general satisfaction
    if summary["average_rating"] < 3:

        guidance.append(
            "Overall satisfaction is low. Improve clarity, "
            "accuracy and usefulness of explanations."
        )

    elif summary["average_rating"] >= 4:

        guidance.append(
            "Citizen satisfaction is good. Maintain the "
            "current clear and helpful response style."
        )

    # Identify areas for improvement
    if negative > positive:

        guidance.append(
            "Negative feedback is higher than positive feedback. "
            "Pay extra attention to answering the citizen's "
            "actual question."
        )

    # Analyse feedback comments
    negative_comments = [
        record["comment"].lower()
        for record in feedback_records
        if record["rating"] <= 2 and record["comment"]
    ]

    detail_keywords = [
        "short",
        "brief",
        "more detail",
        "detailed",
        "explain more",
        "not enough information"
    ]

    clarity_keywords = [
        "confusing",
        "unclear",
        "difficult to understand",
        "complicated"
    ]

    accuracy_keywords = [
        "wrong",
        "incorrect",
        "inaccurate",
        "not correct"
    ]

    if any(
        keyword in comment
        for comment in negative_comments
        for keyword in detail_keywords
    ):

        guidance.append(
            "Citizens have requested more detailed explanations. "
            "Provide step-by-step guidance and explain procedures "
            "more clearly when the knowledge base supports it."
        )

    if any(
        keyword in comment
        for comment in negative_comments
        for keyword in clarity_keywords
    ):

        guidance.append(
            "Some citizens found explanations confusing. "
            "Use simpler language, shorter sentences and "
            "clear headings."
        )

    if any(
        keyword in comment
        for comment in negative_comments
        for keyword in accuracy_keywords
    ):

        guidance.append(
            "Citizens raised concerns about accuracy. "
            "Use only retrieved government information and "
            "clearly identify missing information."
        )

    # Default guidance if no specific pattern was detected
    if not guidance:

        guidance.append(
            "Continue improving response quality while "
            "maintaining accuracy and using official sources."
        )

    return {
        "adaptation_active": True,
        "reason": "Feedback analysis completed.",
        "guidance": " ".join(guidance),
        "feedback_summary": summary
    }


# ==========================================
# 10. TEST DATABASE
# ==========================================

if __name__ == "__main__":

    init_db()

    print("\nFEEDBACK SUMMARY:")
    print(get_feedback_summary())

    print("\nRECENT FEEDBACK RECORDS:")
    for record in get_feedback_records():
        print(record)

    print("\nADAPTATION GUIDANCE:")
    print(get_adaptation_guidance())
