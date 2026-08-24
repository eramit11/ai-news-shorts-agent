from __future__ import annotations

import argparse
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
    """
    Load previously used story URLs.

    This prevents the same news story from being selected
    repeatedly on future runs.
    """

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
    """Create a unique directory for each execution."""

    run_id = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    run_dir = (
        OUTPUT_DIR / run_id
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return run_dir


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    # --------------------------------------------------------
    # Arguments
    # --------------------------------------------------------

    parser = argparse.ArgumentParser(
        description=(
            "AI News YouTube Shorts Agent"
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Generate the complete Short locally "
            "but skip YouTube upload."
        ),
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Settings
    # --------------------------------------------------------

    settings = get_settings()

    # ========================================================
    # OPENROUTER
    # ========================================================

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
    # CREATE OUTPUT DIRECTORY
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

    stories = fetch_stories(
        settings.news_lookback_hours
    )

    if not stories:

        raise RuntimeError(
            "No AI news stories found."
        )

    print(
        f"News stories fetched: {len(stories)}",
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

    # --------------------------------------------------------
    # Remove stories already used
    # --------------------------------------------------------

    fresh_stories = [
        story
        for story in stories
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

        fresh_stories = stories

    # ========================================================
    # RANK NEWS
    # ========================================================

    candidates = rank_stories(
        fresh_stories,
        settings.top_stories,
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

    # --------------------------------------------------------
    # IMPORTANT
    #
    # story_number is 1-based.
    #
    # story_number 1 -> candidates[0]
    # story_number 2 -> candidates[1]
    # etc.
    # --------------------------------------------------------

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

    # IMPORTANT:
    #
    # We do NOT trust the AI-generated source name.
    #
    # The real source comes from the RSS feed.
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

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

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

        voiceover=voiceover,

        source=lead_source,

        out_file=image_file,
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

    generate_tts(
        text=voiceover,

        out_file=audio_file,

        voice=settings.tts_voice,
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

        seconds=settings.short_seconds,
    )

    # ========================================================
    # DRY RUN
    # ========================================================

    if args.dry_run:

        print(
            "",
            flush=True,
        )

        print(
            "======================================",
            flush=True,
        )

        print(
            "DRY RUN COMPLETE",
            flush=True,
        )

        print(
            "======================================",
            flush=True,
        )

        print(
            f"Editorial : {editorial_file}",
            flush=True,
        )

        print(
            f"Image     : {image_file}",
            flush=True,
        )

        print(
            f"Voice     : {audio_file}",
            flush=True,
        )

        print(
            f"Video     : {video_file}",
            flush=True,
        )

        print(
            "",
            flush=True,
        )

        print(
            f"Title: {youtube_title}",
            flush=True,
        )

        print(
            f"Source: {lead_source}",
            flush=True,
        )

        print(
            f"Source URL: {lead_url}",
            flush=True,
        )

        print(
            "",
            flush=True,
        )

        print(
            "YouTube upload was skipped.",
            flush=True,
        )

        return

    # ========================================================
    # YOUTUBE
    # ========================================================

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

    from .youtube import (
        get_youtube,
        upload_short,
    )

    youtube = get_youtube(
        settings.youtube_client_secret_file,

        settings.youtube_token_file,
    )

    # ========================================================
    # DESCRIPTION
    # ========================================================

    # Always append the real source URL.
    #
    # This prevents the AI from being the final authority
    # on the source attribution.
    # ========================================================

    source_attribution = (
        f"\n\nSource: {lead_source}\n"
        f"{lead_url}"
    )

    final_description = (
        description
        + source_attribution
    )

    # ========================================================
    # UPLOAD
    # ========================================================

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

        privacy_status=(
            settings.youtube_privacy_status
        ),

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

    # ========================================================
    # UPLOAD SUCCESS
    # ========================================================

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

    if video_id:

        print(
            f"Video ID: {video_id}",
            flush=True,
        )

        print(
            "YouTube URL:",
            flush=True,
        )

        print(
            f"https://www.youtube.com/watch?v={video_id}",
            flush=True,
        )

    print(
        f"Privacy: "
        f"{settings.youtube_privacy_status}",
        flush=True,
    )

    # ========================================================
    # UPDATE HISTORY
    # ========================================================

    existing_urls = history.get(
        "urls",
        [],
    )

    # --------------------------------------------------------
    # Save actual source URLs from the selected top 3.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Remove duplicates and keep last 500.
    # --------------------------------------------------------

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


if __name__ == "__main__":
    main()