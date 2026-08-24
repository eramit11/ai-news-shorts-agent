# AI News → Viral YouTube Shorts Agent

This project automates a daily AI-news Shorts pipeline:

1. Fetch fresh AI news from Google News RSS.
2. Select the strongest 3 stories.
3. Use OpenRouter (or OpenAI) to create original editorial copy and a viral angle.
4. Generate a professional 9:16 text-based news graphic with Pillow.
5. Generate voice-over with Edge TTS using the selected voice/language.
6. Convert the graphic + narration into a vertical MP4 with FFmpeg.
7. Upload the MP4 to YouTube through the YouTube Data API.
8. Keep a history file so the same story is not repeatedly selected.

## Important

YouTube Shorts are videos, not just image files. This agent therefore turns the generated 9:16 image into a short vertical MP4 with subtle motion and narration.

## Requirements

- Python 3.11+
- FFmpeg on PATH
- OpenAI API key
- Google Cloud project with YouTube Data API v3 enabled
- YouTube OAuth 2.0 client credentials

## Setup

### Linux / macOS

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the environment template:

```bash
cp .env.example .env
```

Add your API/OAuth credentials to `.env`. Never commit `.env`, OAuth tokens, or client secrets.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Start the Application

The current web application is started from the project root.

### Linux / macOS

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Start the UI/API application:

```bash
python -m ui.app
```

The terminal will show the local URL. Open that URL in your browser.

If the project uses the frontend development server separately, open a second terminal:

```bash
cd ui
npm install
npm run dev
```

Keep the backend/API process running while the frontend is running.

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
python -m ui.app
```

## CLI / YouTube Publishing

For the CLI pipeline, place Google's OAuth client JSON at `client_secret.json` when required and run:

```bash
python -m app.main --dry-run
python -m app.main
```

The first publishing run opens the Google OAuth consent flow and creates `token.json`.

## Current Dynamic User Inputs

The web UI sends the user's selected values through the generation pipeline.

Supported generation settings include:

- Topic / custom topic
- Audio language
- Narration tone
- Voice
- Number of stories
- Video duration
- Visual style
- YouTube upload on/off
- YouTube privacy

Important behavior:

- **On-screen visual text is always English.**
- **Voice-over language follows the user's selected audio language.**
- Hindi/Hinglish selection affects narration/TTS, not the text rendered on the video.
- Visual key takeaways are generated separately from the voice-over.
- Topic selection is passed into news ranking/filtering rather than being treated as a fixed `top-ai-news` generation value.

## Daily automation

A GitHub Actions workflow is included at `.github/workflows/daily.yml`. It runs at 11:00 IST (05:30 UTC), with a **Run workflow** button for manual testing. A web host is not needed: GitHub Actions starts a clean Ubuntu machine for each daily run, generates the Short, and uploads it to YouTube.

Store these GitHub Actions secrets:

- `OPENROUTER_API_KEY`
- `YOUTUBE_TOKEN_JSON_B64`
- `YOUTUBE_CLIENT_SECRET_JSON_B64`

The token and client-secret JSON should be base64 encoded before adding them as secrets.

To set up the scheduler:

1. Create a private GitHub repository and push this project to it. Do not commit `.env`, `token.json`, or `client_secret.json`.
2. In GitHub, open **Settings → Secrets and variables → Actions** and add the secrets above. On Linux/macOS, create the values with `base64 -w 0 token.json` and `base64 -w 0 client_secret.json`; on macOS use `base64 < token.json | tr -d '\n'`.
3. Open **Actions → Daily AI News Short → Run workflow**. Confirm that YouTube receives a private test upload and that the generated video is available as a workflow artifact.
4. Change `YOUTUBE_PRIVACY_STATUS` in `.github/workflows/daily.yml` from `private` to `public` only when you are satisfied with the automated uploads.

GitHub may delay scheduled workflows during periods of heavy load; use the manual run button whenever you need an exact start time.

## Content strategy

The editorial agent:
- prefers meaningful AI launches, research, models, major company moves, regulation, safety and funding;
- avoids duplicate stories;
- uses original wording;
- does not invent facts;
- creates a single lead story for the visual;
- uses curiosity-driven hooks without requiring false “breaking news” claims.

## Project structure

- `ui/app.py` — web UI/API entry point
- `app/main.py` — CLI pipeline orchestration
- `app/news.py` — RSS collection/ranking
- `app/editor.py` — OpenAI editorial agent
- `app/media.py` — Pillow news graphics, Edge TTS and FFmpeg
- `app/youtube.py` — OAuth/upload
- `app/config.py` — environment configuration
- `.github/workflows/daily.yml` — daily schedule


## OpenRouter option

The editorial/text step can use OpenRouter instead of OpenAI:

```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openrouter/free
```

OpenRouter is used through its OpenAI-compatible chat-completions endpoint.

**Current limitation:** this project still uses OpenAI for image generation and TTS. Therefore
a dry run will require `OPENAI_API_KEY` after the editorial step. If you want a fully
OpenAI-free pipeline, the next change should replace image generation and TTS with free/local
alternatives.
