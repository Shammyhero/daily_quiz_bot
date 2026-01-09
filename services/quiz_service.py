from typing import Optional
from db import get_connection
from models import Question

class QuizService:
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
            return Question(*row)
        return None

    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, track, difficulty, question_text, canonical_answer, explanation FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Question(*row)
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
        
        def normalize(text):
            # Remove common markdown characters that might be in DB but not in message.text (or vice versa)
            return text.replace('*', '').replace('_', '').replace('`', '').strip()

        norm_message = normalize(message_text)
        
        for row in rows:
            q = Question(*row)
            norm_question = normalize(q.question_text)
            
            # Check if normalized question text is in normalized message text
            if norm_question in norm_message:
                return q
        return None
