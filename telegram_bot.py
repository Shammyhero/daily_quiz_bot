import os
import asyncio
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from services.user_service import UserService
from services.quiz_service import QuizService
from services.progress_service import ProgressService
from llm.evaluator import LLMEvaluator

# Initialize Services (Globally available but initialized safely)
user_service = UserService()
quiz_service = QuizService()
progress_service = ProgressService()
llm_evaluator = None # Will be initialized in create_app

async def post_init(application):
    """Sets the bot commands in the menu."""
    commands = [
        BotCommand("start", "Start/Restart & Settings"),
        BotCommand("track", "Change tracks"),
        BotCommand("stats", "Check progress & streak"),
        BotCommand("help", "Get help"),
        BotCommand("stop", "Pause daily quizzes")
    ]
    await application.bot.set_my_commands(commands)

async def send_initial_questions(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Helper to send initial questions after setup or time change."""
    db_user = user_service.get_user(user_id)
    current_tracks = db_user.track.split(',') if db_user and db_user.track else []
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if db_user and db_user.last_sent_date == today_str:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ **Settings Updated!**\n\n"
                 "You have already received your daily challenge today.\n"
                 "I will send your next question tomorrow!",
            parse_mode='Markdown'
        )
        return

    sent_count = 0
    if current_tracks:
        # Send questions for selected tracks immediately
        for track in current_tracks:
            track = track.strip()
            if not track: continue
            
            q = quiz_service.get_next_question_for_user(user_id, track)
            if q:
                msg = f"📅 **Daily {track.upper()} Challenge**\n\n" \
                      f"🔹 **Difficulty:** {q.difficulty.upper()}\n\n" \
                      f"{q.question_text}\n\n" \
                      f"👇 _Reply with your answer/code!_"
                await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
                sent_count += 1
        
        if sent_count > 0:
            user_service.update_last_sent_date(user_id, today_str)

    await context.bot.send_message(
        chat_id=user_id,
        text="✅ **Setup Complete!**\n\n"
             f"I have sent {sent_count} question(s) to get you started.\n"
             "Good luck!",
        parse_mode='Markdown'
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_service.register_user(user.id)
    
    # Get current tracks to show checkmarks
    db_user = user_service.get_user(user.id)
    current_tracks = db_user.track.split(',') if db_user and db_user.track else []
    
    sql_mark = "✅" if "sql" in current_tracks else "⬜"
    py_mark = "✅" if "python" in current_tracks else "⬜"
    
    welcome_text = (
        f"🚀 **Welcome to the Data Engineering Coach, {user.first_name}!**\n\n"
        "I'm here to help you stay sharp by sending you **one high-quality thinking question** every day.\n\n"
        "📖 **How it works:**\n"
        "1. Select your tracks below.\n"
        "2. Tell me what time you want to be challenged.\n"
        "3. Reply to my questions with your logic/code.\n"
        "4. I'll evaluate your answer using AI and track your progress!\n\n"
        "**Choose your learning tracks:**"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"{sql_mark} SQL", callback_data='track_sql')],
        [InlineKeyboardButton(f"{py_mark} Python", callback_data='track_python')],
        [InlineKeyboardButton("Done / Next ➡️", callback_data='track_done')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Called from callback
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def track_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == 'track_done':
        # Ask for time preference
        context.user_data['awaiting_time'] = True
        await query.edit_message_text(
            "⏰ **One last thing!**\n\n"
            "At what time would you like to receive your daily questions?\n"
            "_(Server time is usually UTC)_\n\n"
            "👉 **Reply with HH:MM** (24-hour format, e.g., `09:00` or `18:30`).\n"
            "Type **'skip'** to use default (09:00).",
            parse_mode='Markdown'
        )
        return

    track_to_toggle = data.split('_')[1]
    
    # Toggle logic
    user_service.toggle_track(user_id, track_to_toggle)
    
    # Refresh the keyboard
    await start(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global llm_evaluator
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Check if we are awaiting time input
    if context.user_data.get('awaiting_time'):
        input_text = user_text.strip().lower()
        if input_text == 'skip':
            user_service.set_preferred_time(user_id, '09:00')
            await update.message.reply_text("👌 Default time (09:00) selected.")
        elif re.match(r'^\d{2}:\d{2}$', input_text):
            # Validate ranges
            h, m = map(int, input_text.split(':'))
            if 0 <= h <= 23 and 0 <= m <= 59:
                user_service.set_preferred_time(user_id, input_text)
                await update.message.reply_text(f"🕒 Time set to {input_text}.")
            else:
                await update.message.reply_text("❌ Invalid time. Please use HH:MM (00:00 - 23:59).")
                return
        else:
            await update.message.reply_text("❌ Invalid format. Please use HH:MM (e.g., 09:00) or type 'skip'.")
            return
        
        # Clear state and proceed to finish setup
        context.user_data['awaiting_time'] = False
        await send_initial_questions(user_id, context)
        return

    user = user_service.get_user(user_id)
    if not user or not user.track:
        await update.message.reply_text("Please use /start to register and choose a track first.")
        return

    # Identify active tracks
    user_tracks = [t.strip() for t in user.track.split(',') if t.strip()]
    if not user_tracks:
         await update.message.reply_text("No tracks selected. Use /track to select SQL or Python.")
         return

    # Find pending questions for all active tracks
    pending_questions = []
    for track in user_tracks:
        q = quiz_service.get_next_question_for_user(user.id, track)
        if q:
            pending_questions.append(q)
    
    if not pending_questions:
        await update.message.reply_text("🎉 You have completed all questions in your selected tracks!")
        return

    # Filter pending questions if user replied to a specific question message
    if update.message.reply_to_message and update.message.reply_to_message.text:
        reply_text = update.message.reply_to_message.text
        # Determine question from the replied message text if possible
        target_question = quiz_service.get_question_from_message_text(reply_text)
        
        if target_question:
            # Check if this specific question is already answered
            if quiz_service.is_question_answered_by_user(user_id, target_question.id):
                await update.message.reply_text("✅ You have already answered this question!")
                return
            
            # If not answered, this is the ONLY question we care about, regardless of track "pending" status
            # This handles cases where the user replies to a question that might not be the "next" one in the queue
            # (though normally it should be, unless they have multiple pending).
            pending_questions = [target_question]

    # Initialize LLM
    if llm_evaluator is None:
        llm_evaluator = LLMEvaluator()
    
    await update.message.reply_chat_action(action="typing")

    # CHECK FOR HINT REQUEST
    if user_text.lower().strip() in ['hint', 'help', 'clue', 'direction']:
        response = ""
        for q in pending_questions:
            hint_text = await llm_evaluator.generate_hint(q.question_text, q.canonical_answer)
            response += f"🔍 **Hint for {q.track.upper()}:**\n{hint_text}\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        return

    # Evaluate against all pending questions (or the filtered one) to find the best match
    best_result = None
    best_confidence = -1.0
    best_question = None
    
    for question in pending_questions:
        # We assume the evaluator gives a low confidence if the answer 
        # is completely unrelated (e.g. Python code for SQL question)
        evaluation = await llm_evaluator.evaluate_answer(
            question_text=question.question_text,
            canonical_answer=question.canonical_answer,
            user_answer=user_text
        )
        
        conf = evaluation.get("confidence", 0.0)
        # If is_correct is True, confidence should be high.
        
        if conf > best_confidence:
            best_confidence = conf
            best_result = evaluation
            best_question = question
    
    # Use the best match
    if best_question and best_result:
        is_correct = best_result.get("is_correct", False)
        feedback = best_result.get("short_feedback", "")
        # hint = best_result.get("hint", "") # We don't use the automatic hint anymore
        
        if is_correct:
            # Record success
            quiz_service.record_answer(user.id, best_question.id, user_text, True, best_confidence)
            
            response = f"✅ **Correct!** ({best_question.track.upper()})\n\n{feedback}\n\n" \
                       f"💡 **Explanation:** {best_question.explanation}\n\n" \
                       f"See you tomorrow!"
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            # Incorrect - Ask if they want a hint
            response = f"❌ **Incorrect.** ({best_question.track.upper()})\n\n{feedback}\n\n" \
                       f"👉 _Need a nudge? Reply with **'hint'** for a clue!_"
            
            await update.message.reply_text(response, parse_mode='Markdown')
    else:
        await update.message.reply_text("⚠️ Could not evaluate your answer. Please try again.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = progress_service.get_user_stats(user_id)
    
    # Calculate fire emojis based on streak (e.g. 1 fire per 3 days, max 5)
    fire_count = min(5, stats['current_streak'] // 3) + 1 if stats['current_streak'] > 0 else 0
    fires = "🔥" * fire_count
    
    text = (
        f"📊 **Your Progress Stats**\n\n"
        f"🏆 **Current Streak:** {stats['current_streak']} days {fires}\n"
        f"──────────────────\n"
        f"✅ **Correct:** {stats['total_correct']}\n"
        f"❌ **Incorrect:** {stats['total_incorrect']}\n"
        f"📝 **Total Answered:** {stats['total_answered']}\n"
        f"🎯 **Accuracy:** {stats['accuracy']}%\n"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_service.set_active_status(user_id, False)
    await update.message.reply_text("⏸️ Daily quizzes paused. Use /start or /track to resume.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "/start - Register and choose track\n"
        "/track - Change your learning track\n"
        "/stats - View your progress\n"
        "/stop - Pause daily messages"
    )
    await update.message.reply_text(text)

def create_app():
    global llm_evaluator
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables.")
    
    # Initialize LLM evaluator here after env vars are loaded
    llm_evaluator = LLMEvaluator()
        
    app = ApplicationBuilder().token(token).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", start)) # Reuse start for track selection
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("help", help_command))
    
    app.add_handler(CallbackQueryHandler(track_callback, pattern='^track_'))
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    return app
