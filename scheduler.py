from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.user_service import UserService
from services.quiz_service import QuizService
from datetime import datetime
import asyncio
from telegram.ext import Application

class DailyQuizScheduler:
    def __init__(self, application: Application, user_service: UserService, quiz_service: QuizService):
        self.application = application
        self.user_service = user_service
        self.quiz_service = quiz_service
        self.scheduler = AsyncIOScheduler()

    def start(self):
        # Run every 10 minutes to check if users need a question
        # For testing, we can make this more frequent, but 10m is reasonable for "Daily"
        # In production, maybe run at specific UTC time.
        # We will use an interval here to ensure we catch up if bot was down.
        self.scheduler.add_job(self.send_daily_quizzes, 'interval', minutes=10)
        self.scheduler.start()
        print("Scheduler started.")

    async def send_daily_quizzes(self):
        print("Running daily quiz job...")
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_time_str = now.strftime("%H:%M")
        
        users = self.user_service.get_active_users_for_daily_quiz(today)
        
        print(f"Found {len(users)} potential users to send quizzes to.")
        
        for user in users:
            # Check preferred time
            # If preferred_time is set (e.g. "09:00"), we only send if current_time >= preferred_time.
            # This is a simple check. Since the job runs every 10 mins, it will eventually catch it.
            # Users with preferred_time in the future (e.g. 18:00) will be skipped until then.
            # Users with preferred_time in the past (e.g. 09:00 and it's 10:00) will be processed immediately.
            
            user_time = user.preferred_time or "09:00"
            if current_time_str < user_time:
                continue

            try:
                # Handle multiple tracks (e.g., "sql,python")
                user_tracks = user.track.split(',') if user.track else []
                
                for track in user_tracks:
                    track = track.strip()
                    if not track: continue
                    
                    question = self.quiz_service.get_next_question_for_user(user.id, track)
                    
                    if not question:
                        continue
                    
                    # Send the question
                    message_text = f"📅 **Daily {track.upper()} Challenge**\n\n" \
                                   f"🔹 **Difficulty:** {question.difficulty.upper()}\n\n" \
                                   f"{question.question_text}\n\n" \
                                   f"👇 _Reply with your answer/code!_"
                    
                    await self.application.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_text,
                        parse_mode="Markdown"
                    )
                    
                    # Small delay between messages
                    await asyncio.sleep(0.5)
                
                # Update last sent date (done once per user per day, regardless of track count)
                self.user_service.update_last_sent_date(user.telegram_id, today)
                
            except Exception as e:
                print(f"Failed to send quiz to user {user.telegram_id}: {e}")
                # In real app, handle 'user blocked bot' here (Forbidden error)
                # and mark user as inactive.
