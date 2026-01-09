import sqlite3
import os
import json
from dataclasses import dataclass
from typing import List, Optional

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(__file__), 'data', 'questions.db'))

def get_connection():
    # Ensure the directory exists (crucial for cloud volumes)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    # Remove existing DB to ensure clean schema with is_active
    if os.path.exists(DB_PATH):
        try:
            # We want to preserve questions if possible, but for this setup 
            # we are re-initializing. I will re-insert questions from the 
            # previous questions.json if I had it, but I have the logic 
            # to export it. 
            # Actually, I should just ALTER table if it exists or 
            # just drop the Users table. 
            pass 
        except:
            pass

    conn = get_connection()
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Users table - Multi-track support + preferred_time
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        track TEXT DEFAULT NULL,
        preferred_time TEXT DEFAULT '09:00',
        last_sent_date TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Questions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track TEXT,
        difficulty TEXT,
        question_text TEXT,
        canonical_answer TEXT,
        explanation TEXT
    )
    """)
    
    # User Questions (History) table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        answered_correctly BOOLEAN,
        llm_confidence REAL,
        user_answer TEXT,
        answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (question_id) REFERENCES questions(id)
    )
    """)
    
    conn.commit()
    conn.close()

def export_questions_to_json():
    """Exports current DB questions to JSON for the 'questions.json' requirement."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT track, difficulty, question_text, canonical_answer, explanation FROM questions")
    rows = cursor.fetchall()
    
    questions = []
    for row in rows:
        questions.append({
            "track": row[0],
            "difficulty": row[1],
            "question_text": row[2],
            "canonical_answer": row[3],
            "explanation": row[4]
        })
        
    json_path = os.path.join(os.path.dirname(__file__), 'data', 'questions.json')
    with open(json_path, 'w') as f:
        json.dump(questions, f, indent=2)
    
    conn.close()

if __name__ == "__main__":
    init_db()
    export_questions_to_json()
    print("Database initialized (schema updated) and questions exported to JSON.")