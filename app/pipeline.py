from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from .config import get_settings
from .editor import build_editorial
from .media import (
    generate_image,
    generate_tts,
    make_short,
)
from .news import (
    fetch_stories,
    rank_stories,
)
from .youtube import (
    get_youtube,
    upload_short,
)


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = ROOT / "output"
HISTORY_FILE = ROOT / "history.json"


# ============================================================
# HISTORY
# ============================================================

def load_history() -> dict:
    """Load previously used story URLs."""

    if not HISTORY_FILE.exists():
        return {
            "urls": []
        }

    try:
        data = json.loads(
            HISTORY_FILE.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(data, dict):
            return {
                "urls": []
            }

        return data

    except Exception:
        return {
            "urls": []
        }


def save_history(history: dict) -> None:
    """Save story history."""

    HISTORY_FILE.write_text(
        json.dumps(
            history,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

def create_run_directory() -> Path:
    """Create a unique output directory."""

    run_id = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    run_dir = OUTPUT_DIR / run_id

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return run_dir


# ============================================================
# PIPELINE
# ============================================================

def run_pipeline(
    topic: str = "top-ai-news",
    language: str = "english",
    tone: str = "natural",
    voice: str | None = None,
    stories: int = 3,
    duration: int = 24,
    visual_style: str = "modern-news",
    upload: bool = False,
    privacy: str = "private",
) -> dict:
    """
    Run the AI News Shorts pipeline.

    This is the UI-facing equivalent of the existing
    app.main workflow.

    The existing CLI pipeline remains untouched.

    Parameters
    ----------
    topic:
        Requested news topic.

    language:
        Requested narration language.

    tone:
        Requested narration tone.

    voice:
        Edge TTS voice.

    stories:
        Number of stories to consider.

    duration:
        Short duration in seconds.

    visual_style:
        Visual style requested by UI.

    upload:
        Whether to upload the generated Short to YouTube.

    privacy:
        YouTube privacy status.
    """

    # ========================================================
    # BASIC VALIDATION
    # ========================================================

    topic = (
        str(topic).strip()
        or "top-ai-news"
    )

    language = (
        str(language).strip()
        or "english"
    )

    tone = (
        str(tone).strip()
        or "natural"
    )

    visual_style = (
        str(visual_style).strip()
        or "modern-news"
    )

    try:
        stories = int(stories)
    except (TypeError, ValueError):
        stories = 3

    stories = max(
        1,
        min(stories, 10),
    )

    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = 24

    duration = max(
        5,
        min(duration, 180),
    )

    # ========================================================
    # SETTINGS
    # ========================================================

    settings = get_settings()

    if (
        settings.ai_provider.lower()
        != "openrouter"
    ):
        raise RuntimeError(
            "AI_PROVIDER must be set to openrouter."
        )

    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing."
        )

    # ========================================================
    # OPENROUTER
    # ========================================================

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=(
            "https://openrouter.ai/api/v1"
        ),
        default_headers={
            "HTTP-Referer":
                "https://github.com/ai-news-shorts-agent",
            "X-Title":
                "AI News Shorts Agent",
        },
    )

    # ========================================================
    # OUTPUT DIRECTORY
    # ========================================================

    run_dir = create_run_directory()

    print(
        f"Output directory: {run_dir}",
        flush=True,
    )

    # ========================================================
    # FETCH NEWS
    # ========================================================

    print(
        "Fetching AI news...",
        flush=True,
    )

    news_lookback = (
        settings.news_lookback_hours
    )

    fetched_stories = fetch_stories(
        news_lookback
    )

    if not fetched_stories:
        raise RuntimeError(
            "No AI news stories found."
        )

    print(
        f"News stories fetched: "
        f"{len(fetched_stories)}",
        flush=True,
    )

    # ========================================================
    # HISTORY
    # ========================================================

    history = load_history()

    used_urls = set(
        history.get(
            "urls",
            [],
        )
    )

    fresh_stories = [
        story
        for story in fetched_stories
        if story.url not in used_urls
    ]

    if fresh_stories:

        print(
            f"Unused stories available: "
            f"{len(fresh_stories)}",
            flush=True,
        )

    else:

        print(
            "All stories were previously used.",
            flush=True,
        )

        print(
            "Using current stories again.",
            flush=True,
        )

        fresh_stories = fetched_stories

    # ========================================================
    # TOPIC FILTER
    # ========================================================

    # "top-ai-news" means use the normal configured feeds.
    #
    # For now, we deliberately do not perform an aggressive
    # keyword filter because that could accidentally remove
    # relevant stories from the existing working pipeline.
    #
    # Topic-specific feed filtering can be added later without
    # changing the rest of this pipeline.

    normalized_topic = topic.lower().strip()

    print(
        f"Topic: {topic}",
        flush=True,
    )

    # ========================================================
    # RANK NEWS
    # ========================================================

    candidates = rank_stories(
    fresh_stories,
    stories,
    topic=topic,
)

    if not candidates:
        raise RuntimeError(
            "No ranked news candidates available."
        )

    print(
        f"Candidates sent to editorial AI: "
        f"{len(candidates)}",
        flush=True,
    )

    # ========================================================
    # EDITORIAL AI
    # ========================================================

    editorial = build_editorial(
    client=client,
    candidates=candidates,
    model=settings.openrouter_model,
    provider=settings.ai_provider,
    language=language,
    tone=tone,
    topic=topic,
)

    print(
        "Editorial generated successfully.",
        flush=True,
    )

    # ========================================================
    # SAVE EDITORIAL
    # ========================================================

    editorial_file = (
        run_dir / "editorial.json"
    )

    editorial_file.write_text(
        json.dumps(
            editorial,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"Editorial saved: {editorial_file}",
        flush=True,
    )

    # ========================================================
    # VALIDATE LEAD
    # ========================================================

    lead = editorial.get(
        "lead"
    )

    if not isinstance(
        lead,
        dict,
    ):
        raise RuntimeError(
            "Editorial does not contain a valid lead object."
        )

    lead_story_number = editorial.get(
        "lead_story_number"
    )

    if not isinstance(
        lead_story_number,
        int,
    ):
        raise RuntimeError(
            "lead_story_number is missing or invalid."
        )

    if not (
        1
        <= lead_story_number
        <= len(candidates)
    ):
        raise RuntimeError(
            "Invalid lead_story_number: "
            f"{lead_story_number}"
        )

    lead_story = candidates[
        lead_story_number - 1
    ]

    # ========================================================
    # REAL SOURCE
    # ========================================================

    lead_source = lead_story.source
    lead_url = lead_story.url

    print(
        f"Lead story: {lead_story.title} "
        f"- {lead_source}",
        flush=True,
    )

    print(
        f"Lead URL: {lead_url}",
        flush=True,
    )

    # ========================================================
    # LEAD CONTENT
    # ========================================================

    headline = lead.get(
        "headline",
        "",
    ).strip()

    hook = lead.get(
        "hook",
        "",
    ).strip()

    voiceover = lead.get(
        "voiceover",
        "",
    ).strip()

    visual_concept = lead.get(
        "visual_concept",
        "",
    ).strip()
    
    key_takeaways = lead.get(
    "key_takeaways",
    [],
)

    if not isinstance(key_takeaways, list):
        key_takeaways = []

    key_takeaways = [
        str(item).strip()
        for item in key_takeaways
        if str(item).strip()
    ][:3]

    youtube_title = lead.get(
        "youtube_title",
        headline or "AI News",
    ).strip()

    description = lead.get(
        "description",
        "",
    ).strip()

    hashtags = lead.get(
        "hashtags",
        [
            "#AI",
            "#ArtificialIntelligence",
            "#TechNews",
            "#Shorts",
        ],
    )

    # ========================================================
    # UI LANGUAGE / TONE
    # ========================================================

    # The current build_editorial() interface does not expose
    # language/tone parameters.
    #
    # We preserve the existing editorial implementation here
    # so the working CLI behavior is not broken.
    #
    # These values are returned to the UI and are ready for
    # the next editorial enhancement.

    print(
        f"Language: {language}",
        flush=True,
    )

    print(
        f"Tone: {tone}",
        flush=True,
    )

    print(
        f"Visual style: {visual_style}",
        flush=True,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    if not headline:
        raise RuntimeError(
            "Lead headline is empty."
        )

    if not hook:
        raise RuntimeError(
            "Lead hook is empty."
        )

    if not voiceover:
        raise RuntimeError(
            "Lead voiceover is empty."
        )

    # ========================================================
    # IMAGE
    # ========================================================

    image_file = (
        run_dir / "visual.png"
    )

    print(
        "",
        flush=True,
    )

    print(
        "======================================",
        flush=True,
    )

    print(
        "STEP 1/3 — TEXT NEWS GRAPHIC",
        flush=True,
    )

    print(
        "======================================",
        flush=True,
    )

    generate_image(
        prompt=visual_concept,
        headline=headline,
        hook=hook,
        key_takeaways=key_takeaways,
        source=lead_source,
        out_file=image_file,
        visual_style=visual_style,
    )

    # ========================================================
    # TTS
    # ========================================================

    audio_file = (
        run_dir / "voice.mp3"
    )

    print(
        "",
        flush=True,
    )

    print(
        "======================================",
        flush=True,
    )

    print(
        "STEP 2/3 — VOICE",
        flush=True,
    )

    print(
        "======================================",
        flush=True,
    )

    # Use the UI-selected voice when supplied.
    #
    # Otherwise use the configured .env voice.
    selected_voice = (
        voice
        or settings.tts_voice
    )

    generate_tts(
        text=voiceover,
        out_file=audio_file,
        voice=selected_voice,
    )

    # ========================================================
    # VIDEO
    # ========================================================

    video_file = (
        run_dir / "short.mp4"
    )

    print(
        "",
        flush=True,
    )

    print(
        "======================================",
        flush=True,
    )

    print(
        "STEP 3/3 — VIDEO",
        flush=True,
    )

    print(
        "======================================",
        flush=True,
    )

    make_short(
        image=image_file,
        audio=audio_file,
        out_video=video_file,
        seconds=duration,
        headline=headline,
        hook=hook,
        key_takeaways=key_takeaways,
        source=lead_source,
    )

    # ========================================================
    # RESULT
    # ========================================================

    result = {
        "success": True,
        "run_directory": str(run_dir),
        "editorial_file": str(
            editorial_file
        ),
        "image_file": str(
            image_file
        ),
        "audio_file": str(
            audio_file
        ),
        "video_file": str(
            video_file
        ),
        "title": youtube_title,
        "headline": headline,
        "hook": hook,
        "source": lead_source,
        "source_url": lead_url,
        "topic": topic,
        "language": language,
        "tone": tone,
        "voice": selected_voice,
        "duration": duration,
        "visual_style": visual_style,
        "youtube_uploaded": False,
        "youtube_url": None,
        "youtube_video_id": None,
        "privacy": privacy,
    }

    # ========================================================
    # YOUTUBE
    # ========================================================

    if upload:

        print(
            "",
            flush=True,
        )

        print(
            "======================================",
            flush=True,
        )

        print(
            "YOUTUBE",
            flush=True,
        )

        print(
            "======================================",
            flush=True,
        )

        print(
            "Authenticating with YouTube...",
            flush=True,
        )

        youtube = get_youtube(
            settings.youtube_client_secret_file,
            settings.youtube_token_file,
        )

        # ----------------------------------------------------
        # REAL SOURCE ATTRIBUTION
        # ----------------------------------------------------

        source_attribution = (
            f"\n\nSource: {lead_source}\n"
            f"{lead_url}"
        )

        final_description = (
            description
            + source_attribution
        )

        print(
            "Uploading Short to YouTube...",
            flush=True,
        )

        upload_response = upload_short(
            youtube=youtube,
            video_file=video_file,
            title=youtube_title,
            description=final_description,
            hashtags=hashtags,
            privacy_status=privacy,
            category_id=(
                settings.youtube_category_id
            ),
            language=(
                settings.youtube_language
            ),
        )

        video_id = upload_response.get(
            "id"
        )

        result[
            "youtube_uploaded"
        ] = True

        result[
            "youtube_video_id"
        ] = video_id

        if video_id:

            result[
                "youtube_url"
            ] = (
                "https://www.youtube.com/watch?v="
                + video_id
            )

            print(
                "",
                flush=True,
            )

            print(
                "======================================",
                flush=True,
            )

            print(
                "YOUTUBE UPLOAD SUCCESSFUL",
                flush=True,
            )

            print(
                "======================================",
                flush=True,
            )

            print(
                f"Video ID: {video_id}",
                flush=True,
            )

            print(
                "YouTube URL:",
                flush=True,
            )

            print(
                result["youtube_url"],
                flush=True,
            )

        print(
            f"Privacy: {privacy}",
            flush=True,
        )

    else:

        print(
            "",
            flush=True,
        )

        print(
            "YouTube upload skipped.",
            flush=True,
        )

    # ========================================================
    # UPDATE HISTORY
    # ========================================================

    existing_urls = history.get(
        "urls",
        [],
    )

    for story in editorial.get(
        "top3",
        [],
    ):

        story_number = story.get(
            "story_number"
        )

        if not isinstance(
            story_number,
            int,
        ):
            continue

        if not (
            1
            <= story_number
            <= len(candidates)
        ):
            continue

        actual_story = candidates[
            story_number - 1
        ]

        existing_urls.append(
            actual_story.url
        )

    history["urls"] = list(
        dict.fromkeys(
            existing_urls
        )
    )[-500:]

    save_history(
        history
    )

    print(
        "Story history updated.",
        flush=True,
    )

    return result