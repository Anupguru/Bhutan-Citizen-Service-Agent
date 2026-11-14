
import sqlite3
from pathlib import Path
from datetime import datetime


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "memory" / "agent_memory.db"


# ==========================================
# 1. INITIALIZE DATABASE
# ==========================================

def init_db():

    connection = sqlite3.connect(DB_PATH)

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

            rating INTEGER NOT NULL,

            comment TEXT,

            timestamp TEXT NOT NULL,

            FOREIGN KEY (interaction_id)
            REFERENCES interactions(id)
        )
    """)

    connection.commit()
    connection.close()


# ==========================================
# 2. SAVE INTERACTION
# ==========================================

def save_interaction(
    session_id,
    query,
    response,
    tools_used
):

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO interactions
        (session_id, query, response, tools_used, timestamp)

        VALUES (?, ?, ?, ?, ?)
    """, (
        session_id,
        query,
        response,
        ", ".join(tools_used),
        datetime.now().isoformat()
    ))

    interaction_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return interaction_id


# ==========================================
# 3. SAVE CITIZEN FEEDBACK
# ==========================================

def save_feedback(
    interaction_id,
    rating,
    comment=""
):

    if rating not in [1, 2, 3, 4, 5]:
        raise ValueError("Rating must be between 1 and 5.")

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO feedback
        (interaction_id, rating, comment, timestamp)

        VALUES (?, ?, ?, ?)
    """, (
        interaction_id,
        rating,
        comment,
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()


# ==========================================
# 4. RETRIEVE RECENT CONVERSATIONS
# ==========================================

def get_recent_interactions(
    session_id,
    limit=5
):

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

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
# 5. RETRIEVE ALL INTERACTIONS
# ==========================================

def get_all_interactions():

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

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
# 6. CALCULATE FEEDBACK STATISTICS
# ==========================================

def get_feedback_summary():

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(*),
            AVG(rating),
            SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END)

        FROM feedback
    """)

    result = cursor.fetchone()

    total = result[0] or 0
    average = result[1] or 0
    positive = result[2] or 0

    connection.close()

    return {
        "total_feedback": total,
        "average_rating": round(average, 2),
        "positive_feedback": positive
    }


# ==========================================
# 7. TEST DATABASE
# ==========================================

if __name__ == "__main__":

    init_db()

    print("SQLite database initialized successfully!")

    interaction_id = save_interaction(
        session_id="test_session",
        query="I want to apply for a passport",
        response="Here is the passport application guidance.",
        tools_used=[
            "search_services",
            "get_service_details"
        ]
    )

    print("Interaction saved:", interaction_id)

    save_feedback(
        interaction_id=interaction_id,
        rating=5,
        comment="The guidance was helpful."
    )

    print("\nRecent interactions:")

    history = get_recent_interactions(
        "test_session"
    )

    for item in history:
        print(item)

    print("\nFeedback summary:")

    print(get_feedback_summary())
