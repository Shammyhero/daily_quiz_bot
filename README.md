# Daily Data Engineering Quiz Bot

A disciplined daily training bot for SQL and Python (Data Engineering focus).
It sends one unique question per day, evaluates answers using OpenAI, and tracks progress.

## Features
- 📅 **Daily Schedule**: Sends one question automatically per day.
- 🧠 **AI Evaluation**: Uses OpenAI to grade logic (not just syntax).
- 📊 **Progress Tracking**: Tracks accuracy and completed questions.
- 🛡️ **Anti-Repetition**: Never sends the same question twice to the same user.
- ⏸️ **Pause/Resume**: Users can control their subscription.

## Prerequisites
- Python 3.9+
- SQLite3
- OpenAI API Key
- Telegram Bot Token

## Installation

1. **Clone the repository**
   ```bash
   git clone <repo_url>
   cd daily_quiz_bot
   ```

2. **Install Dependencies**
   ```bash
   pip install python-telegram-bot apscheduler openai
   ```

3. **Environment Variables**
   Create a `.env` file or export variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
   export OPENAI_API_KEY="your_openai_api_key"
   ```

## Usage

1. **Initialize Database & Seed Data**
   The bot automatically initializes `data/questions.db` on first run.
   
   To explicitly reset/re-seed:
   ```bash
   python3 db.py
   ```

2. **Run the Bot**
   ```bash
   python3 main.py
   ```

## Project Structure
- `main.py`: Entry point.
- `telegram_bot.py`: Telegram handlers.
- `scheduler.py`: Daily job logic.
- `llm/evaluator.py`: OpenAI integration.
- `services/`: Business logic.
- `data/`: Database and JSON seed.

## Customization
- **Questions**: Edit `data/questions.json`.
- **Scheduler**: Adjusted in `scheduler.py`.
