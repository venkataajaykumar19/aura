# Deploying AURA to Render Free Tier

This guide provides step-by-step instructions to push AURA to GitHub and deploy the web dashboard to Render's free tier.

> [!WARNING]
> **Ephemeral Storage on Render Free Tier**: Render free instances do not have persistent disk storage. The local SQLite database (`aura.db`) resets whenever the service spins down or redeploys.
>
> **Telegram Bot & 8 AM Briefing Scheduler**: Render's free tier web service is intended for incoming HTTP requests and sleeps after 15 minutes of inactivity. The Telegram long-polling bot and 8 AM daily briefing scheduler do **not** run as background workers on Render free web services. Keep the Telegram bot running locally (`python -m backend.run_telegram`) or run it on a separate always-on server/VPS.

---

## Step 1: Initialize Git and Push to GitHub

1. Open your terminal in the project root:
   ```bash
   cd c:\Users\ajayk\OneDrive\Desktop\AURA
   ```

2. Initialize Git and stage all project files:
   ```bash
   git init
   git add .
   ```

3. Confirm that sensitive files are ignored (verify `.env` and `aura.db` are **NOT** staged):
   ```bash
   git status
   ```
   *(Ensure only source code, `.env.example`, `render.yaml`, `requirements.txt`, etc. are staged — never `.env` or `*.db`).*

4. Commit your changes:
   ```bash
   git commit -m "feat: complete AURA voice assistant (Phases 1-18)"
   ```

5. Rename branch to `main`, link your GitHub repository, and push:
   ```bash
   git branch -M main
   git remote add origin https://github.com/<your-username>/aura.git
   git push -u origin main
   ```

---

## Step 2: Create a Free Web Service on Render

1. Log in to your Render account at **[dashboard.render.com](https://dashboard.render.com/)**.
2. Click **New +** in the top navigation and select **Web Service**.
3. Choose **Build and deploy from a Git repository** and connect your `aura` GitHub repository.
4. Configure service details:
   - **Name**: `aura` (or a custom name like `aura-assistant`)
   - **Region**: Select the region closest to you (e.g. `Singapore` or `Frankfurt`)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`

---

## Step 3: Configure Environment Variables on Render

In the **Environment Variables** section of your new web service on Render, add the following variables:

| Variable Key | Required | Value / Instructions |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | **Yes** | `3.11.9` |
| `GEMINI_API_KEY` | **Yes** | Your Google AI Studio API key |
| `AURA_PASSWORD` | **Yes** | The password/PIN you use to unlock your web dashboard |
| `GOOGLE_CLIENT_ID` | Optional | Your Google Cloud OAuth Client ID (for Gmail & Calendar) |
| `GOOGLE_CLIENT_SECRET` | Optional | Your Google Cloud OAuth Client Secret (for Gmail & Calendar) |
| `TELEGRAM_BOT_TOKEN` | Optional | Your Telegram bot token from BotFather |

Click **Save Changes**.

---

## Step 4: Add Authorized Redirect URI in Google Cloud Console

If you are using Google Calendar or Gmail integration:

1. Copy your live Render URL from the top of the Render dashboard (e.g., `https://aura-xxxx.onrender.com`).
2. Go to **[Google Cloud Console — Credentials](https://console.cloud.google.com/apis/credentials)**.
3. Open your OAuth 2.0 Web Client ID.
4. Under **Authorized redirect URIs**, click **+ Add URI** and add:
   ```text
   https://<your-render-url>.onrender.com/api/oauth/callback
   ```
   *(Keep `http://localhost:8000/api/oauth/callback` in the list so local development continues working).*
5. Click **Save**.

---

## Step 5: Test the Live Deployment

1. Once Render finishes building and reports `Live`, click your service URL (or navigate to `https://<your-render-url>.onrender.com`).
2. **Health Check**: Open `https://<your-render-url>.onrender.com/api/health` — it should return:
   ```json
   {"status": "ok", "service": "AURA v1"}
   ```
3. **Login Protection**: Visiting `https://<your-render-url>.onrender.com/` will redirect to `/login`.
4. **Unlock**: Enter your `AURA_PASSWORD` and click **Unlock**. You will be redirected to the full AURA dashboard.

---

## Running the Telegram Bot Locally

Because Render's free tier web service sleeps when idle, run the Telegram bot on your local machine:
```bash
.\.venv\Scripts\python -m backend.run_telegram
```
The bot will poll Telegram in real-time, handle voice notes with Gemini transcription, and dispatch the 8:00 AM daily briefing.
