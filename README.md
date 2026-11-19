# AURA — Personal AI Assistant

A calm, warm, voice-first personal AI assistant.

## Requirements
- Python 3.11+

## Getting Started

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   - `GEMINI_API_KEY`: Free key from [Google AI Studio](https://aistudio.google.com/)
   - `TELEGRAM_BOT_TOKEN`: Free token from [@BotFather](https://t.me/BotFather) on Telegram
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: Optional OAuth client for Gmail & Calendar

4. **Run the services (Two Terminals):**

   - **Terminal 1 (FastAPI Server & Web Dashboard):**
     ```bash
     uvicorn backend.main:app --reload
     ```
     Navigate to [http://localhost:8000](http://localhost:8000).

   - **Terminal 2 (Telegram Bot Runner):**
     ```bash
     python -m backend.run_telegram
     ```
