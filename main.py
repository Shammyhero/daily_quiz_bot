import os
from dotenv import load_dotenv
# Load environment variables before any other imports
load_dotenv()

import asyncio
import logging
from db import init_db
from telegram_bot import create_app, user_service, quiz_service
from scheduler import DailyQuizScheduler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    # 1. Initialize DB
    print("Initializing Database...")
    init_db()
    
    # 2. Create Bot Application
    print("Creating Bot Application...")
    application = create_app()
    
    # 3. Start Scheduler
    # We need to pass the application to the scheduler so it can send messages
    print("Starting Scheduler...")
    scheduler = DailyQuizScheduler(application, user_service, quiz_service)
    scheduler.start()
    
    # 4. Run Bot
    print("Bot is polling...")
    application.run_polling()

if __name__ == "__main__":
    # Ensure env vars are set
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("Error: TELEGRAM_BOT_TOKEN is not set.")
    elif not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set.")
    else:
        main()
