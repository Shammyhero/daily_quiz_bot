from typing import Optional, List
from db import get_connection
from models import User

class UserService:
    def get_user(self, telegram_id: int) -> Optional[User]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, telegram_id, track, preferred_time, last_sent_date, is_active, created_at FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Convert 0/1 to boolean for is_active (index 5)
            row_list = list(row)
            row_list[5] = bool(row_list[5])
            # Handle preferred_time default if null? DB default '09:00' handles it.
            return User(*row_list)
        return None

    def register_user(self, telegram_id: int):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Default is_active=1, preferred_time='09:00' via schema default
            cursor.execute("INSERT OR IGNORE INTO users (telegram_id, is_active) VALUES (?, 1)", (telegram_id,))
            conn.commit()
        finally:
            conn.close()

    def set_preferred_time(self, telegram_id: int, time_str: str):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET preferred_time = ? WHERE telegram_id = ?", (time_str, telegram_id))
            conn.commit()
        finally:
            conn.close()


    def set_track(self, telegram_id: int, track: str):
        # This legacy method might be used, but we should update logic or deprecate.
        # For compatibility with existing calls, we'll treat it as "replace".
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET track = ?, is_active = 1 WHERE telegram_id = ?", (track, telegram_id))
            conn.commit()
        finally:
            conn.close()

    def toggle_track(self, telegram_id: int, track_to_toggle: str) -> str:
        """
        Toggles a track for the user.
        Returns the new comma-separated track string.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT track FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            current_tracks_str = row[0] if row and row[0] else ""
            
            tracks = set(current_tracks_str.split(',')) if current_tracks_str else set()
            tracks.discard('') # Remove empty strings if any
            
            if track_to_toggle in tracks:
                tracks.remove(track_to_toggle)
            else:
                tracks.add(track_to_toggle)
            
            new_tracks_str = ",".join(sorted(tracks))
            
            # If no tracks left, maybe set inactive? Or just empty string.
            # Let's keep is_active=1 unless explicitly stopped.
            
            cursor.execute("UPDATE users SET track = ? WHERE telegram_id = ?", (new_tracks_str, telegram_id))
            conn.commit()
            
            return new_tracks_str
        finally:
            conn.close()

    def set_active_status(self, telegram_id: int, is_active: bool):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_active = ? WHERE telegram_id = ?", (is_active, telegram_id))
            conn.commit()
        finally:
            conn.close()

    def update_last_sent_date(self, telegram_id: int, date_str: str):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET last_sent_date = ? WHERE telegram_id = ?", (date_str, telegram_id))
            conn.commit()
        finally:
            conn.close()
            
    def get_active_users_for_daily_quiz(self, today_str: str) -> List[User]:
        """
        Get users who are active, have a track selected, and haven't received a question today.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, telegram_id, track, preferred_time, last_sent_date, is_active, created_at 
            FROM users 
            WHERE is_active = 1 
              AND track IS NOT NULL 
              AND (last_sent_date IS NULL OR last_sent_date != ?)
        """, (today_str,))
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            row_list = list(row)
            row_list[5] = bool(row_list[5]) # is_active is now at index 5
            users.append(User(*row_list))
        return users

    def get_total_users_count(self) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count