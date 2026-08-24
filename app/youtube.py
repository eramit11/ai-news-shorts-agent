from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]


# ============================================================
# YOUTUBE AUTHENTICATION
# ============================================================

def get_youtube(
    client_secret_file: str,
    token_file: str,
):

    creds = None

    # --------------------------------------------------------
    # Existing OAuth token
    # --------------------------------------------------------

    if os.path.exists(token_file):

        creds = (
            Credentials
            .from_authorized_user_file(
                token_file,
                SCOPES,
            )
        )

    # --------------------------------------------------------
    # Refresh expired token
    # --------------------------------------------------------

    if (
        creds
        and creds.expired
        and creds.refresh_token
    ):

        creds.refresh(
            Request()
        )

        # Save refreshed credentials.
        with open(
            token_file,
            "w",
            encoding="utf-8",
        ) as f:

            f.write(
                creds.to_json()
            )

    # --------------------------------------------------------
    # First-time OAuth
    # --------------------------------------------------------

    if not creds or not creds.valid:

        if not os.path.exists(
            client_secret_file
        ):

            raise FileNotFoundError(
                "Missing YouTube OAuth client "
                f"secret file: {client_secret_file}"
            )

        flow = (
            InstalledAppFlow
            .from_client_secrets_file(
                client_secret_file,
                SCOPES,
            )
        )

        creds = flow.run_local_server(
            port=0
        )

        with open(
            token_file,
            "w",
            encoding="utf-8",
        ) as f:

            f.write(
                creds.to_json()
            )

    # --------------------------------------------------------
    # Build YouTube API client
    # --------------------------------------------------------

    youtube = build(
        "youtube",
        "v3",
        credentials=creds,
    )

    return youtube


# ============================================================
# UPLOAD SHORT
# ============================================================

def upload_short(
    youtube,
    video_file: Path,
    title: str,
    description: str,
    hashtags: list[str] | None = None,
    privacy_status: str = "private",
    category_id: str = "28",
    language: str = "en",
    tags: list[str] | None = None,
):

    video_file = Path(
        video_file
    )

    # --------------------------------------------------------
    # Validate video
    # --------------------------------------------------------

    if not video_file.exists():

        raise FileNotFoundError(
            f"Video file not found: {video_file}"
        )

    if video_file.stat().st_size == 0:

        raise RuntimeError(
            f"Video file is empty: {video_file}"
        )

    # --------------------------------------------------------
    # Normalize hashtags
    # --------------------------------------------------------

    hashtags = hashtags or []

    # Remove # for YouTube tags.
    clean_hashtags = [
        str(tag).lstrip("#").strip()
        for tag in hashtags
        if str(tag).strip()
    ]

    # --------------------------------------------------------
    # Support both `hashtags` and `tags`
    #
    # This keeps compatibility with older code.
    # --------------------------------------------------------

    if tags:

        clean_tags = [
            str(tag).lstrip("#").strip()
            for tag in tags
            if str(tag).strip()
        ]

    else:

        clean_tags = clean_hashtags.copy()

    # --------------------------------------------------------
    # Add hashtags to description if they aren't already there
    # --------------------------------------------------------

    hashtag_text = " ".join(
        f"#{tag}"
        for tag in clean_hashtags
    )

    final_description = (
        description or ""
    ).strip()

    if hashtag_text:

        if final_description:

            final_description += (
                "\n\n"
                + hashtag_text
            )

        else:

            final_description = (
                hashtag_text
            )

    # --------------------------------------------------------
    # YouTube metadata
    # --------------------------------------------------------

    body = {

        "snippet": {

            "title": (
                title or "AI News Short"
            )[:100],

            "description": (
                final_description
            ),

            "tags": clean_tags,

            "categoryId": str(
                category_id
            ),

            "defaultLanguage": (
                language
            ),

            "defaultAudioLanguage": (
                language
            ),
        },

        "status": {

            "privacyStatus": (
                privacy_status
            ),

            "selfDeclaredMadeForKids": False,
        },
    }

    # --------------------------------------------------------
    # Media upload
    # --------------------------------------------------------

    media = MediaFileUpload(
        str(video_file),
        chunksize=-1,
        resumable=True,
        mimetype="video/mp4",
    )

    print(
        "Uploading Short to YouTube...",
        flush=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None

    while response is None:

        status, response = (
            request.next_chunk()
        )

        if status:

            progress = int(
                status.progress() * 100
            )

            print(
                f"Upload progress: "
                f"{progress}%",
                flush=True,
            )

    return response