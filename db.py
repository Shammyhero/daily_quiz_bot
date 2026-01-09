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

def seed_questions():
    """Seeds the database from data/questions.json if the questions table is empty."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if questions already exist
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    json_path = os.path.join(os.path.dirname(__file__), 'data', 'questions.json')
    if not os.path.exists(json_path):
        print(f"Warning: {json_path} not found. No questions seeded.")
        conn.close()
        return

    with open(json_path, 'r') as f:
        questions = json.load(f)

    for q in questions:
        cursor.execute("""
            INSERT INTO questions (track, difficulty, question_text, canonical_answer, explanation)
            VALUES (?, ?, ?, ?, ?)
        """, (q['track'], q['difficulty'], q['question_text'], q['canonical_answer'], q['explanation']))
    
    conn.commit()
    conn.close()
    print(f"Seeded {len(questions)} questions from JSON.")

def init_db():
    # ... (existing setup code)
    conn = get_connection()
    cursor = conn.cursor()
    # (tables creation code stays here)
    conn.commit()
    conn.close()
    
    # Seed data
    seed_questions()

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