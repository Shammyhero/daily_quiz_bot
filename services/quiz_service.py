import json
import os
import re
from typing import Optional
from db import get_connection
from models import Question

class QuizService:
    def __init__(self):
        # Load formatted questions into memory for runtime text swapping
        self.format_map = {}
        try:
            json_path = os.path.join(os.path.dirname(__file__), '../data', 'questions.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    for q in data:
                        # Key: Normalized text (no backticks, lower, collapsed spaces)
                        # Value: The beautifully formatted text from JSON
                        norm_key = self._normalize(q['question_text'])
                        self.format_map[norm_key] = q['question_text']
        except Exception as e:
            print(f"Warning: Could not load questions.json for formatting: {e}")

    def _normalize(self, text):
        """Standardizes text for matching: lower case, no backticks, single spaces."""
        if not text: return ""
        text = text.replace('`', '')
        text = re.sub(r'\s+', ' ', text).strip()
        return text.lower()

    def _apply_formatting(self, question: Question) -> Question:
        """Swaps the DB text with the formatted JSON text if a match is found."""
        if not question: return None
        
        # Try to find a better formatted version of the question text
        key = self._normalize(question.question_text)
        if key in self.format_map:
            question.question_text = self.format_map[key]
            
        return question

    def get_next_question_for_user(self, user_id: int, track: str) -> Optional[Question]:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Select a question that has NOT been answered by this user
        query = """
        SELECT id, track, difficulty, question_text, canonical_answer, explanation
        FROM questions q
        WHERE q.track = ?
          AND q.id NOT IN (
              SELECT question_id FROM user_questions WHERE user_id = ?
          )
        ORDER BY q.id ASC
        LIMIT 1
        """
        
        cursor.execute(query, (track, user_id))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._apply_formatting(Question(*row))
        return None

    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, track, difficulty, question_text, canonical_answer, explanation FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._apply_formatting(Question(*row))
        return None

    def record_answer(self, user_id: int, question_id: int, user_answer: str, is_correct: bool, confidence: float):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO user_questions (user_id, question_id, answered_correctly, llm_confidence, user_answer)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, question_id, is_correct, confidence, user_answer))
            conn.commit()
        finally:
            conn.close()
    
    def is_question_answered_by_user(self, user_id: int, question_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM user_questions WHERE user_id = ? AND question_id = ?", (user_id, question_id))
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def get_question_from_message_text(self, message_text: str) -> Optional[Question]:
        """
        Identifies a question if the question_text is a substring of the message_text.
        Useful for determining which question a user is replying to.
        Uses normalization to handle Markdown formatting differences.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, track, difficulty, question_text, canonical_answer, explanation FROM questions")
        rows = cursor.fetchall()
        conn.close()
        
        # We need to normalize the message text the same way
        norm_message = self._normalize(message_text)
        
        for row in rows:
            q = Question(*row)
            # Normalize the DB question text
            norm_question = self._normalize(q.question_text)
            
            # Check if normalized question text is in normalized message text
            if norm_question in norm_message:
                return self._apply_formatting(q)
        return None
