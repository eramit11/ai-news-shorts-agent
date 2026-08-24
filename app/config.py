from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


# Load .env from the project root.
load_dotenv()


@dataclass
class Settings:

    # =====================================================
    # AI PROVIDER
    # =====================================================

    ai_provider: str

    # OpenRouter
    openrouter_api_key: str
    openrouter_model: str

    # Legacy OpenAI fields retained for compatibility.
    # They are NOT required when AI_PROVIDER=openrouter.
    openai_key: str
    text_model: str
    image_model: str
    tts_model: str

    # =====================================================
    # TTS
    # =====================================================

    tts_voice: str

    # =====================================================
    # YOUTUBE
    # =====================================================

    youtube_client_secret_file: str
    youtube_token_file: str
    youtube_privacy_status: str
    youtube_category_id: str
    youtube_language: str

    # =====================================================
    # VIDEO
    # =====================================================

    short_seconds: int

    # =====================================================
    # NEWS
    # =====================================================

    news_lookback_hours: int
    top_stories: int


def get_settings() -> Settings:

    # =====================================================
    # AI PROVIDER
    # =====================================================

    ai_provider = os.getenv(
        "AI_PROVIDER",
        "openrouter",
    ).strip().lower()

    # =====================================================
    # API KEYS
    # =====================================================

    openai_key = os.getenv(
        "OPENAI_API_KEY",
        "",
    ).strip()

    openrouter_api_key = os.getenv(
        "OPENROUTER_API_KEY",
        "",
    ).strip()

    # =====================================================
    # OPENROUTER
    # =====================================================

    openrouter_model = os.getenv(
        "OPENROUTER_MODEL",
        "openai/gpt-oss-20b:free",
    ).strip()

    # =====================================================
    # LEGACY OPENAI SETTINGS
    #
    # These remain here only so older code doesn't break.
    # They are NOT used by our current free media pipeline.
    # =====================================================

    text_model = os.getenv(
        "OPENAI_TEXT_MODEL",
        "gpt-5-mini",
    ).strip()

    image_model = os.getenv(
        "OPENAI_IMAGE_MODEL",
        "gpt-image-1",
    ).strip()

    tts_model = os.getenv(
        "OPENAI_TTS_MODEL",
        "gpt-4o-mini-tts",
    ).strip()

    # =====================================================
    # EDGE TTS
    #
    # IMPORTANT:
    # Use TTS_VOICE, NOT OPENAI_TTS_VOICE.
    # =====================================================

    tts_voice = os.getenv(
        "TTS_VOICE",
        "en-US-ChristopherNeural",
    ).strip()

    # =====================================================
    # YOUTUBE
    # =====================================================

    youtube_client_secret_file = os.getenv(
        "YOUTUBE_CLIENT_SECRET_FILE",
        "client_secret.json",
    ).strip()

    youtube_token_file = os.getenv(
        "YOUTUBE_TOKEN_FILE",
        "token.json",
    ).strip()

    youtube_privacy_status = os.getenv(
        "YOUTUBE_PRIVACY_STATUS",
        "private",
    ).strip().lower()

    youtube_category_id = os.getenv(
        "YOUTUBE_CATEGORY_ID",
        "28",
    ).strip()

    youtube_language = os.getenv(
        "YOUTUBE_LANGUAGE",
        "en",
    ).strip()

    # =====================================================
    # VIDEO
    # =====================================================

    try:

        short_seconds = int(
            os.getenv(
                "SHORT_SECONDS",
                "24",
            )
        )

    except ValueError:

        short_seconds = 24

    if short_seconds <= 0:
        short_seconds = 24

    # =====================================================
    # NEWS
    # =====================================================

    try:

        news_lookback_hours = int(
            os.getenv(
                "NEWS_LOOKBACK_HOURS",
                "30",
            )
        )

    except ValueError:

        news_lookback_hours = 30

    if news_lookback_hours <= 0:
        news_lookback_hours = 30

    try:

        top_stories = int(
            os.getenv(
                "TOP_STORIES",
                "3",
            )
        )

    except ValueError:

        top_stories = 3

    if top_stories <= 0:
        top_stories = 3

    # =====================================================
    # VALIDATION
    # =====================================================

    if ai_provider == "openrouter":

        if not openrouter_api_key:

            raise RuntimeError(
                "AI_PROVIDER=openrouter but "
                "OPENROUTER_API_KEY is missing."
            )

    elif ai_provider == "openai":

        if not openai_key:

            raise RuntimeError(
                "AI_PROVIDER=openai but "
                "OPENAI_API_KEY is missing."
            )

    else:

        raise RuntimeError(
            f"Unsupported AI_PROVIDER: {ai_provider}"
        )

    # =====================================================
    # RETURN SETTINGS
    # =====================================================

    return Settings(

        ai_provider=ai_provider,

        openrouter_api_key=openrouter_api_key,
        openrouter_model=openrouter_model,

        openai_key=openai_key,

        text_model=text_model,
        image_model=image_model,
        tts_model=tts_model,

        tts_voice=tts_voice,

        youtube_client_secret_file=(
            youtube_client_secret_file
        ),

        youtube_token_file=(
            youtube_token_file
        ),

        youtube_privacy_status=(
            youtube_privacy_status
        ),

        youtube_category_id=(
            youtube_category_id
        ),

        youtube_language=(
            youtube_language
        ),

        short_seconds=short_seconds,

        news_lookback_hours=(
            news_lookback_hours
        ),

        top_stories=top_stories,
    )