from typing import Dict, Any
from db import get_connection

class ProgressService:
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Total answered
        cursor.execute("SELECT COUNT(*) FROM user_questions WHERE user_id = ?", (user_id,))
        total_answered = cursor.fetchone()[0]
        
        # Correct answers
        cursor.execute("SELECT COUNT(*) FROM user_questions WHERE user_id = ? AND answered_correctly = 1", (user_id,))
        total_correct = cursor.fetchone()[0]
        
        # Streak Calculation
        # Get distinct dates where user answered at least one question
        cursor.execute("""
            SELECT DISTINCT date(answered_at) as activity_date 
            FROM user_questions 
            WHERE user_id = ? 
            ORDER BY activity_date DESC
        """, (user_id,))
        rows = cursor.fetchall()
        
        conn.close()
        
        from datetime import datetime, timedelta
        
        activity_dates = [datetime.strptime(r[0], "%Y-%m-%d").date() for r in rows]
        
        streak = 0
        if activity_dates:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # Check if the most recent activity is today or yesterday to keep streak alive
            if activity_dates[0] == today or activity_dates[0] == yesterday:
                streak = 1
                current_check = activity_dates[0]
                
                # Iterate through rest to find consecutive days
                for i in range(1, len(activity_dates)):
                    prev_date = activity_dates[i]
                    expected_date = current_check - timedelta(days=1)
                    
                    if prev_date == expected_date:
                        streak += 1
                        current_check = prev_date
                    else:
                        break
            else:
                # Streak broken (last activity was before yesterday)
                streak = 0

        accuracy = 0.0
        if total_answered > 0:
            accuracy = (total_correct / total_answered) * 100
            
        return {
            "total_answered": total_answered,
            "total_correct": total_correct,
            "total_incorrect": total_answered - total_correct,
            "accuracy": round(accuracy, 2),
            "current_streak": streak
        }
