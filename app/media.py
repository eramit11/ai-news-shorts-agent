from __future__ import annotations

import asyncio
import subprocess
import textwrap
from pathlib import Path

import edge_tts

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter,
)


# ============================================================
# FONT CONFIGURATION
# ============================================================

FONT_DIRS = [
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation2"),
]


def find_font(
    names: list[str],
    size: int,
):
    for directory in FONT_DIRS:
        for name in names:
            path = directory / name

            if path.exists():
                return ImageFont.truetype(
                    str(path),
                    size,
                )

    return ImageFont.load_default()


FONT_BOLD = [
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
]

FONT_REGULAR = [
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
]


# ============================================================
# VISUAL TEXT VALIDATION
# ============================================================

def validate_visual_text(field_name: str, value: str) -> str:
    """
    Validate text that will appear on-screen.

    On-screen text must remain English/Latin.
    Voiceover may use the selected audio language.
    """

    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    for char in text:
        code = ord(char)

        # Basic Latin
        if 0x0000 <= code <= 0x007F:
            continue

        # Latin-1 Supplement
        if 0x0080 <= code <= 0x00FF:
            continue

        # Latin Extended-A
        if 0x0100 <= code <= 0x017F:
            continue

        # Latin Extended-B
        if 0x0180 <= code <= 0x024F:
            continue

        # General punctuation
        if 0x2000 <= code <= 0x206F:
            continue

        # Currency symbols
        if 0x20A0 <= code <= 0x20CF:
            continue

        # Mathematical operators
        if 0x2200 <= code <= 0x22FF:
            continue

        raise RuntimeError(
            f"Visual field '{field_name}' contains "
            "non-English/non-Latin characters. "
            "On-screen text must always be English. "
            "Only the voiceover may use the selected audio language."
        )

    return text


# ============================================================
# BACKGROUND THEMES
# ============================================================
#
# Every Short gets a different professional gradient.
#
# Each theme contains:
#
#   name
#   top color
#   bottom color
#   glow 1
#   glow 2
#   accent
#
# Colors are intentionally controlled rather than completely
# random so the channel maintains a professional visual identity.
# ============================================================

BACKGROUND_THEMES = [
    {
        "name": "blue_purple",
        "top": (8, 18, 55),
        "bottom": (55, 25, 105),
        "glow1": (0, 145, 255, 55),
        "glow2": (125, 70, 255, 45),
        "accent": (80, 195, 255),
    },
    {
        "name": "cyan_teal",
        "top": (4, 38, 52),
        "bottom": (8, 105, 112),
        "glow1": (0, 220, 210, 50),
        "glow2": (0, 150, 255, 35),
        "accent": (75, 225, 215),
    },
    {
        "name": "purple_magenta",
        "top": (38, 10, 60),
        "bottom": (105, 20, 90),
        "glow1": (180, 50, 255, 45),
        "glow2": (255, 50, 150, 35),
        "accent": (220, 110, 255),
    },
    {
        "name": "orange_red",
        "top": (58, 18, 8),
        "bottom": (125, 35, 20),
        "glow1": (255, 120, 20, 55),
        "glow2": (255, 50, 30, 35),
        "accent": (255, 165, 75),
    },
    {
        "name": "deep_red",
        "top": (50, 8, 18),
        "bottom": (105, 18, 35),
        "glow1": (255, 45, 70, 45),
        "glow2": (190, 30, 90, 35),
        "accent": (255, 105, 125),
    },
    {
        "name": "charcoal_slate",
        "top": (10, 15, 22),
        "bottom": (48, 58, 70),
        "glow1": (100, 160, 200, 35),
        "glow2": (150, 120, 255, 25),
        "accent": (150, 205, 235),
    },
    {
        "name": "navy_cyan",
        "top": (6, 20, 48),
        "bottom": (15, 75, 125),
        "glow1": (20, 170, 255, 50),
        "glow2": (40, 90, 255, 35),
        "accent": (80, 205, 255),
    },
    {
        "name": "gold_dark",
        "top": (45, 34, 6),
        "bottom": (105, 82, 12),
        "glow1": (255, 190, 40, 45),
        "glow2": (255, 120, 20, 30),
        "accent": (255, 205, 85),
    },
    {
        "name": "green_tech",
        "top": (5, 35, 22),
        "bottom": (12, 95, 58),
        "glow1": (40, 255, 150, 45),
        "glow2": (20, 180, 120, 35),
        "accent": (80, 235, 150),
    },
    {
        "name": "indigo",
        "top": (15, 12, 55),
        "bottom": (40, 40, 125),
        "glow1": (80, 90, 255, 50),
        "glow2": (150, 80, 255, 35),
        "accent": (130, 155, 255),
    },
]


def get_background_theme(
    out_file: Path,
) -> dict:
    """
    Select a background theme while avoiding the immediately
    previous theme.

    The last selected theme is stored inside the output directory:

        output/.last_background_theme

    This means separate executions of:

        python -m app.main

    will not immediately reuse the same background.
    """

    output_root = out_file.parent.parent

    state_file = output_root / ".last_background_theme"

    previous_index = None

    try:
        if state_file.exists():
            value = state_file.read_text(
                encoding="utf-8"
            ).strip()

            if value:
                previous_index = int(value)

    except Exception:
        previous_index = None

    available_indices = list(
        range(len(BACKGROUND_THEMES))
    )

    if (
        previous_index is not None
        and 0 <= previous_index < len(BACKGROUND_THEMES)
        and len(available_indices) > 1
    ):
        available_indices.remove(
            previous_index
        )

    # Use nanosecond time to vary the selection
    # between independent executions.
    import time

    index = (
        time.time_ns()
        % len(available_indices)
    )

    selected_index = available_indices[index]

    try:
        state_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        state_file.write_text(
            str(selected_index),
            encoding="utf-8",
        )

    except Exception:
        pass

    return BACKGROUND_THEMES[
        selected_index
    ]


# ============================================================
# TEXT WRAPPING
# ============================================================


def wrap_text(
    draw,
    text: str,
    font,
    max_width: int,
):
    words = text.split()

    if not words:
        return []

    lines = []

    current = ""

    for word in words:
        test = (
            word
            if not current
            else current + " " + word
        )

        bbox = draw.textbbox(
            (0, 0),
            test,
            font=font,
        )

        width = (
            bbox[2] - bbox[0]
        )

        if width <= max_width:
            current = test

        else:
            if current:
                lines.append(
                    current
                )

            current = word

    if current:
        lines.append(
            current
        )

    return lines


def draw_wrapped(
    draw,
    text: str,
    x: int,
    y: int,
    font,
    fill,
    max_width: int,
    line_spacing: int = 12,
):
    lines = wrap_text(
        draw,
        text,
        font,
        max_width,
    )

    bbox = font.getbbox(
        "Ag"
    )

    line_height = (
        bbox[3]
        - bbox[1]
        + line_spacing
    )

    for line in lines:
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
        )

        y += line_height

    return y


# ============================================================
# TEXT-BASED NEWS GRAPHIC
# ============================================================


def generate_image(
    prompt: str = "",
    out_file: Path | None = None,
    headline: str | None = None,
    hook: str | None = None,
    key_takeaways: list[str] | None = None,
    source: str | None = None,
    visual_style: str = "modern-news",
) -> Path:

    """
    Generate a professional 1080x1920 text-based AI news
    graphic.

    IMPORTANT:
    This does NOT use an AI image generator.

    Pillow creates the graphic, which means:

    - exact text
    - sharp typography
    - no hallucinated image text
    - consistent branding
    - mobile-friendly layout
    - different gradient background on each run
    """

    if out_file is None:
        raise RuntimeError(
            "out_file is required."
        )

    out_file = Path(
        out_file
    )

    out_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Generating text-based 9:16 AI news graphic...",
        flush=True,
    )

    # --------------------------------------------------------
    # Defaults
    # --------------------------------------------------------

    headline = (
        headline
        or "Latest AI News"
    )

    hook = (
        hook
        or "The latest development in artificial intelligence."
    )

    source = (
        source
        or "AI News"
    )

    # --------------------------------------------------------
    # Canvas
    # --------------------------------------------------------

    WIDTH = 1080
    HEIGHT = 1920

    # --------------------------------------------------------
    # Select NEW background theme
    # --------------------------------------------------------

    theme = get_background_theme(
        out_file
    )

    top = theme["top"]
    bottom = theme["bottom"]
    accent = theme["accent"]

    # --------------------------------------------------------
    # Base image
    # --------------------------------------------------------

    image = Image.new(
        "RGB",
        (
            WIDTH,
            HEIGHT,
        ),
        top,
    )

    draw = ImageDraw.Draw(
        image
    )

    # --------------------------------------------------------
    # Gradient background
    # --------------------------------------------------------

    for y in range(
        HEIGHT
    ):
        ratio = (
            y / max(
                HEIGHT - 1,
                1,
            )
        )

        r = int(
            top[0]
            + (
                bottom[0]
                - top[0]
            )
            * ratio
        )

        g = int(
            top[1]
            + (
                bottom[1]
                - top[1]
            )
            * ratio
        )

        b = int(
            top[2]
            + (
                bottom[2]
                - top[2]
            )
            * ratio
        )

        draw.line(
            [
                (0, y),
                (WIDTH, y),
            ],
            fill=(
                r,
                g,
                b,
            ),
        )

    # --------------------------------------------------------
    # Background glow
    # --------------------------------------------------------

    glow = Image.new(
        "RGBA",
        (
            WIDTH,
            HEIGHT,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    glow_draw = ImageDraw.Draw(
        glow
    )

    glow_draw.ellipse(
        (
            -300,
            100,
            700,
            1000,
        ),
        fill=theme["glow1"],
    )

    glow_draw.ellipse(
        (
            400,
            1150,
            1350,
            2050,
        ),
        fill=theme["glow2"],
    )

    glow = glow.filter(
        ImageFilter.GaussianBlur(
            120
        )
    )

    image = Image.alpha_composite(
        image.convert(
            "RGBA"
        ),
        glow,
    )

    draw = ImageDraw.Draw(
        image
    )

    # --------------------------------------------------------
    # Fonts
    # --------------------------------------------------------

    font_brand = find_font(
        FONT_BOLD,
        46,
    )

    font_label = find_font(
        FONT_BOLD,
        32,
    )

    font_headline = find_font(
        FONT_BOLD,
        76,
    )

    font_hook = find_font(
        FONT_BOLD,
        42,
    )

    font_body = find_font(
        FONT_REGULAR,
        34,
    )

    font_source = find_font(
        FONT_REGULAR,
        28,
    )

    font_footer = find_font(
        FONT_BOLD,
        28,
    )

    margin = 70

    content_width = (
        WIDTH
        - margin * 2
    )

    # ========================================================
    # BRAND HEADER
    # ========================================================

    badge_x = margin
    badge_y = 65

    draw.rounded_rectangle(
        (
            badge_x,
            badge_y,
            badge_x + 290,
            badge_y + 72,
        ),
        radius=36,
        fill=(
            accent[0],
            accent[1],
            accent[2],
            255,
        ),
    )

    draw.text(
        (
            badge_x + 25,
            badge_y + 14,
        ),
        "AI NEWS",
        font=font_brand,
        fill=(
            255,
            255,
            255,
        ),
    )

    draw.text(
        (
            WIDTH - 285,
            87,
        ),
        "DAILY UPDATE",
        font=font_source,
        fill=(
            205,
            215,
            230,
        ),
    )

    # ========================================================
    # SEPARATOR
    # ========================================================

    draw.rounded_rectangle(
        (
            margin,
            180,
            WIDTH - margin,
            188,
        ),
        radius=4,
        fill=(
            accent[0],
            accent[1],
            accent[2],
        ),
    )

    # ========================================================
    # BREAKING LABEL
    # ========================================================

    y = 245

    draw.text(
        (
            margin,
            y,
        ),
        "BREAKING",
        font=font_label,
        fill=(
            accent[0],
            accent[1],
            accent[2],
        ),
    )

    y += 70

    # ========================================================
    # HEADLINE
    # ========================================================

    y = draw_wrapped(
        draw,
        headline,
        margin,
        y,
        font_headline,
        (
            255,
            255,
            255,
        ),
        content_width,
        line_spacing=14,
    )

    # ========================================================
    # WHY THIS MATTERS CARD
    # ========================================================

    card_top = y + 45

    hook_lines = wrap_text(
        draw,
        hook,
        font_hook,
        content_width - 70,
    )

    hook_line_height = 58

    card_height = max(
        155,
        80
        + len(hook_lines)
        * hook_line_height,
    )

    # Slightly transparent dark card works across
    # every background theme.
    draw.rounded_rectangle(
        (
            margin,
            card_top,
            WIDTH - margin,
            card_top + card_height,
        ),
        radius=28,
        fill=(
            12,
            20,
            35,
            235,
        ),
        outline=(
            accent[0],
            accent[1],
            accent[2],
            255,
        ),
        width=3,
    )

    draw.text(
        (
            margin + 30,
            card_top + 22,
        ),
        "WHY THIS MATTERS",
        font=font_label,
        fill=(
            accent[0],
            accent[1],
            accent[2],
        ),
    )

    hook_y = (
        card_top
        + 72
    )

    for line in hook_lines:
        draw.text(
            (
                margin + 30,
                hook_y,
            ),
            line,
            font=font_hook,
            fill=(
                245,
                248,
                255,
            ),
        )

        hook_y += (
            hook_line_height
        )

    # ========================================================
    # KEY TAKEAWAYS
    # ========================================================

    facts_top = (
        card_top
        + card_height
        + 55
    )

    draw.text(
        (
            margin,
            facts_top,
        ),
        "KEY TAKEAWAYS",
        font=font_label,
        fill=(
            accent[0],
            accent[1],
            accent[2],
        ),
    )

    # --------------------------------------------------------
    # English visual key takeaways.
    # IMPORTANT: Never derive visual text from voiceover.
    # Voiceover may be Hindi/Hinglish; on-screen text stays English.
    # --------------------------------------------------------

    key_takeaways = key_takeaways or []

    sentences = [
        str(item).strip()
        for item in key_takeaways
        if str(item).strip()
    ]

    sentences = sentences[:3]

    bullet_y = (
        facts_top
        + 70
    )

    for sentence in sentences:

        if len(sentence) > 190:
            sentence = (
                sentence[:187]
                + "..."
            )

        bullet_lines = wrap_text(
            draw,
            sentence,
            font_body,
            content_width - 70,
        )

        # Bullet
        draw.ellipse(
            (
                margin,
                bullet_y + 10,
                margin + 17,
                bullet_y + 27,
            ),
            fill=(
                accent[0],
                accent[1],
                accent[2],
            ),
        )

        text_y = bullet_y

        for line in bullet_lines:
            draw.text(
                (
                    margin + 38,
                    text_y,
                ),
                line,
                font=font_body,
                fill=(
                    225,
                    232,
                    245,
                ),
            )

            text_y += 48

        bullet_y = (
            text_y
            + 25
        )

    # ========================================================
    # SOURCE
    # ========================================================

    source_top = (
        HEIGHT - 260
    )

    draw.rounded_rectangle(
        (
            margin,
            source_top,
            WIDTH - margin,
            source_top + 95,
        ),
        radius=20,
        fill=(
            12,
            20,
            34,
            240,
        ),
    )

    draw.text(
        (
            margin + 25,
            source_top + 28,
        ),
        "SOURCE",
        font=font_label,
        fill=(
            accent[0],
            accent[1],
            accent[2],
        ),
    )

    source_display = source

    if len(source_display) > 38:
        source_display = (
            source_display[:35]
            + "..."
        )

    draw.text(
        (
            margin + 220,
            source_top + 31,
        ),
        source_display,
        font=font_source,
        fill=(
            235,
            240,
            250,
        ),
    )

    # ========================================================
    # FOOTER
    # ========================================================

    footer_y = (
        HEIGHT - 115
    )

    draw.text(
        (
            margin,
            footer_y,
        ),
        "FOLLOW FOR DAILY AI NEWS",
        font=font_footer,
        fill=(
            190,
            205,
            225,
        ),
    )

    draw.text(
        (
            WIDTH - 265,
            footer_y,
        ),
        "#AI #SHORTS",
        font=font_footer,
        fill=(
            accent[0],
            accent[1],
            accent[2],
        ),
    )

    # ========================================================
    # SAVE
    # ========================================================

    image = image.convert(
        "RGB"
    )

    image.save(
        out_file,
        "PNG",
        optimize=True,
    )

    print(
        f"Text news graphic saved: {out_file}",
        flush=True,
    )

    print(
        f"Background theme: {theme['name']}",
        flush=True,
    )

    return out_file


# ============================================================
# EDGE TTS
# ============================================================


async def _generate_tts(
    text: str,
    output_file: Path,
    voice: str,
):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="+5%",
    )

    await communicate.save(
        str(output_file)
    )


def generate_tts(
    text: str,
    out_file: Path,
    voice: str = "en-US-ChristopherNeural",
) -> Path:

    print(
        "Generating voice with Edge TTS...",
        flush=True,
    )

    if not text:
        raise RuntimeError(
            "Voiceover text is empty."
        )

    out_file = Path(
        out_file
    )

    out_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        asyncio.run(
            _generate_tts(
                text,
                out_file,
                voice,
            )
        )

    except Exception as exc:
        raise RuntimeError(
            "Edge TTS failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if not out_file.exists():
        raise RuntimeError(
            "TTS completed but audio file "
            "was not created."
        )

    if out_file.stat().st_size == 0:
        raise RuntimeError(
            "TTS generated an empty audio file."
        )

    print(
        f"Voice saved: {out_file}",
        flush=True,
    )

    return out_file


# ============================================================
# FFMPEG SHORT
# ============================================================

def make_short(
    image: Path,
    audio: Path,
    out_video: Path,
    seconds: int = 24,
    headline: str = "Latest AI News",
    hook: str = "The latest development in artificial intelligence.",
    key_takeaways: list[str] | None = None,
    source: str = "AI News",
) -> Path:
    """Create a professional animated 9:16 AI-news Short."""

    print(
        "Creating Phase 3 professional 9:16 YouTube Short with FFmpeg...",
        flush=True,
    )

    image = Path(image)
    audio = Path(audio)
    out_video = Path(out_video)

    if not image.exists():
        raise RuntimeError(f"Image file not found: {image}")

    if not audio.exists():
        raise RuntimeError(f"Audio file not found: {audio}")

    out_video.parent.mkdir(parents=True, exist_ok=True)

    try:
        duration = max(1.0, float(seconds))
    except (TypeError, ValueError):
        duration = 24.0

    # --------------------------------------------------------
    # Validate visual text.
    # --------------------------------------------------------

    headline = validate_visual_text("headline", headline)
    hook = validate_visual_text("hook", hook)
    source = validate_visual_text("source", source)

    safe_takeaways = []

    for item in (key_takeaways or []):
        try:
            safe_takeaways.append(
                validate_visual_text("key_takeaway", item)
            )
        except RuntimeError:
            print(
                "WARNING: Skipping non-English key takeaway from video.",
                flush=True,
            )

        if len(safe_takeaways) >= 3:
            break

    if not safe_takeaways:
        safe_takeaways = [
            "Key details from this AI story.",
            "The development could affect the AI industry.",
        ]

    # --------------------------------------------------------
    # Professional motion background.
    #
    # The original visual.png remains the editorial graphic.
    # The video gets its own animated visual treatment.
    # --------------------------------------------------------

    animation_bg = out_video.parent / "motion_background.png"

    # Create a dedicated graphical background.
    #
    # IMPORTANT:
    # Do NOT use visual.png here. visual.png is the editorial
    # text graphic. The video background must remain independent
    # so the headline is never duplicated behind the UI layers.
    import random

    seed = sum(ord(ch) for ch in str(out_video)) + int(duration * 100)
    rng = random.Random(seed)

    palettes = [
        ((7, 15, 30), (12, 48, 72), (0, 220, 255)),
        ((18, 8, 35), (58, 14, 72), (210, 70, 255)),
        ((30, 10, 8), (78, 24, 12), (255, 105, 45)),
        ((5, 28, 24), (10, 66, 52), (35, 225, 170)),
        ((10, 15, 38), (28, 38, 88), (105, 130, 255)),
    ]

    dark, secondary, accent_rgb = rng.choice(palettes)

    # Build a clean vertical gradient with no text.
    small_w, small_h = 270, 480
    bg_small = Image.new("RGB", (small_w, small_h))
    pixels = bg_small.load()

    for y in range(small_h):
        ratio = y / max(1, small_h - 1)

        r = int(dark[0] * (1 - ratio) + secondary[0] * ratio)
        g = int(dark[1] * (1 - ratio) + secondary[1] * ratio)
        b = int(dark[2] * (1 - ratio) + secondary[2] * ratio)

        for x in range(small_w):
            pixels[x, y] = (r, g, b)

    bg = bg_small.resize((1080, 1920), Image.Resampling.BICUBIC).convert("RGBA")

    # Soft atmospheric glow blobs.
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    for _ in range(4):
        cx = rng.randint(-100, 1180)
        cy = rng.randint(-100, 2020)
        radius = rng.randint(180, 430)

        glow_draw.ellipse(
            (
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
            ),
            fill=(*accent_rgb, rng.randint(18, 38)),
        )

    glow = glow.filter(ImageFilter.GaussianBlur(90))
    bg = Image.alpha_composite(bg, glow)

    # Fine technical grid.
    overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    grid_size = rng.choice([72, 84, 96, 108])

    for x in range(0, 1081, grid_size):
        draw.line(
            (x, 0, x, 1920),
            fill=(*accent_rgb, 22),
            width=1,
        )

    for y in range(0, 1921, grid_size):
        draw.line(
            (0, y, 1080, y),
            fill=(*accent_rgb, 22),
            width=1,
        )

    # Large geometric rings/arcs.
    for _ in range(3):
        cx = rng.randint(-150, 1230)
        cy = rng.randint(100, 1900)
        radius = rng.randint(260, 620)
        width = rng.choice([3, 4, 6])

        draw.ellipse(
            (
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
            ),
            outline=(*accent_rgb, rng.randint(28, 60)),
            width=width,
        )

    # Diagonal energy lines.
    for _ in range(4):
        y1 = rng.randint(250, 1750)
        y2 = y1 + rng.randint(-450, 450)

        draw.line(
            (0, y1, 1080, max(0, min(1920, y2))),
            fill=(*accent_rgb, rng.randint(25, 55)),
            width=rng.choice([2, 3, 5]),
        )

    # Small data-node dots for a subtle AI/technology feel.
    for _ in range(24):
        x = rng.randint(40, 1040)
        y = rng.randint(80, 1840)
        radius = rng.choice([2, 3, 4])

        draw.ellipse(
            (
                x - radius,
                y - radius,
                x + radius,
                y + radius,
            ),
            fill=(*accent_rgb, rng.randint(70, 130)),
        )

    # Dark vignette keeps the foreground text highly readable.
    vignette = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette)

    vignette_draw.rectangle(
        (0, 0, 1080, 1920),
        fill=(0, 0, 0, 45),
    )

    bg = Image.alpha_composite(bg, overlay)
    bg = Image.alpha_composite(bg, vignette)

    # Slight blur keeps the graphics atmospheric rather than busy.
    bg = bg.filter(ImageFilter.GaussianBlur(0.35))

    bg.convert("RGB").save(animation_bg, "PNG", optimize=True)

    print(
        "Graphical motion background created:",
        animation_bg,
        flush=True,
    )

    # --------------------------------------------------------
    # Prepare text as PNG overlays.
    # --------------------------------------------------------

    layers_dir = out_video.parent / "motion_layers"
    layers_dir.mkdir(parents=True, exist_ok=True)

    try:
        width = 920
        accent = (0, 210, 255)

        font_regular = find_font(FONT_REGULAR, 38)
        font_small = find_font(FONT_REGULAR, 30)
        font_headline = find_font(FONT_BOLD, 64)
        font_hook = find_font(FONT_BOLD, 42)
        font_takeaway = find_font(FONT_REGULAR, 34)
        font_source = find_font(FONT_REGULAR, 28)

        # ----------------------------------------------------
        # ----------------------------------------------------
        # Headline layer
        # ----------------------------------------------------

        headline_img = Image.new(
            "RGBA",
            (width, 500),
            (0, 0, 0, 0),
        )

        headline_draw = ImageDraw.Draw(headline_img)

        headline_draw.rounded_rectangle(
            (0, 0, width - 1, 499),
            radius=28,
            fill=(12, 18, 30, 235),
            outline=(*accent, 210),
            width=3,
        )

        headline_draw.text(
            (42, 42),
            "AI NEWS",
            font=font_small,
            fill=(*accent, 255),
        )

        headline_lines = textwrap.wrap(
            headline,
            width=25,
        )[:3]

        y = 105

        for line in headline_lines:
            headline_draw.text(
                (42, y),
                line,
                font=font_headline,
                fill=(255, 255, 255, 255),
            )
            y += 78

        headline_path = layers_dir / "headline.png"
        headline_img.save(headline_path, "PNG")

        # ----------------------------------------------------
        # Hook layer
        # ----------------------------------------------------

        hook_img = Image.new(
            "RGBA",
            (width, 300),
            (0, 0, 0, 0),
        )

        hook_draw = ImageDraw.Draw(hook_img)

        hook_draw.rounded_rectangle(
            (0, 0, width - 1, 299),
            radius=24,
            fill=(18, 24, 38, 235),
        )

        hook_lines = textwrap.wrap(
            hook,
            width=38,
        )[:3]

        y = 35

        for line in hook_lines:
            hook_draw.text(
                (36, y),
                line,
                font=font_hook,
                fill=(245, 248, 255, 255),
            )
            y += 60

        hook_path = layers_dir / "hook.png"
        hook_img.save(hook_path, "PNG")

        # ----------------------------------------------------
        # Takeaways layer
        # ----------------------------------------------------

        take_img = Image.new(
            "RGBA",
            (width, 650),
            (0, 0, 0, 0),
        )

        take_draw = ImageDraw.Draw(take_img)

        take_draw.rounded_rectangle(
            (0, 0, width - 1, 649),
            radius=26,
            fill=(10, 16, 28, 238),
        )

        take_draw.text(
            (36, 30),
            "KEY TAKEAWAYS",
            font=font_small,
            fill=(*accent, 255),
        )

        y = 95

        for item in safe_takeaways[:3]:
            wrapped = textwrap.wrap(
                item,
                width=42,
            )[:2]

            take_draw.ellipse(
                (38, y + 8, 54, y + 24),
                fill=(*accent, 255),
            )

            line_y = y

            for line in wrapped:
                take_draw.text(
                    (76, line_y),
                    line,
                    font=font_regular,
                    fill=(245, 248, 255, 255),
                )
                line_y += 44

            y = max(
                y + 72,
                line_y + 15,
            )

        take_path = layers_dir / "takeaways.png"
        take_img.save(take_path, "PNG")

        # ----------------------------------------------------
        # Source/footer layer
        # ----------------------------------------------------

        source_img = Image.new(
            "RGBA",
            (width, 120),
            (0, 0, 0, 0),
        )

        source_draw = ImageDraw.Draw(source_img)

        source_draw.text(
            (30, 30),
            f"Source: {source}",
            font=font_small,
            fill=(190, 198, 215, 255),
        )

        source_path = layers_dir / "source.png"
        source_img.save(source_path, "PNG")

    except Exception as exc:
        raise RuntimeError(
            f"Failed to create motion-design layers: {exc}"
        ) from exc

    # --------------------------------------------------------
    # FFmpeg professional motion design.
    #
    # Background:
    #   slow zoom + horizontal movement
    #
    # Headline:
    #   slides from left + fade
    #
    # Hook:
    #   slides from right + fade
    #
    # Takeaways:
    #   slides upward + fade
    #
    # Source:
    #   fades in near the end
    # --------------------------------------------------------

    inputs = [
        "-loop", "1",
        "-i", str(animation_bg),

        "-loop", "1",
        "-i", str(headline_path),

        "-loop", "1",
        "-i", str(hook_path),

        "-loop", "1",
        "-i", str(take_path),

        "-loop", "1",
        "-i", str(source_path),

        "-i", str(audio),
    ]

    headline_start = 0.20
    hook_start = min(duration * 0.22, 4.0)
    take_start = min(duration * 0.42, 8.0)
    source_start = max(duration - 2.5, duration * 0.82)

    filters = [
        (
            "[0:v]"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "zoompan="
            "z='min(zoom+0.00018,1.045)':"
            "x='iw/2-(iw/zoom/2)+18*sin(on/95)':"
            "y='ih/2-(ih/zoom/2)+12*cos(on/120)':"
            "d=1:"
            "s=1080x1920:"
            "fps=30,"
            "format=rgba"
            "[bg]"
        ),

        (
            f"[1:v]"
            f"format=rgba,"
            f"fade=t=in:st={headline_start:.3f}:d=0.65:alpha=1"
            "[headline]"
        ),

        (
            f"[2:v]"
            f"format=rgba,"
            f"fade=t=in:st={hook_start:.3f}:d=0.65:alpha=1"
            "[hook]"
        ),

        (
            f"[3:v]"
            f"format=rgba,"
            f"fade=t=in:st={take_start:.3f}:d=0.70:alpha=1"
            "[take]"
        ),

        (
            f"[4:v]"
            f"format=rgba,"
            f"fade=t=in:st={source_start:.3f}:d=0.50:alpha=1"
            "[source]"
        ),

        (
            "[bg]"
            "[headline]"
            "overlay="
            "x='if(lt(t,0.20),-980,"
            "if(lt(t,0.85),"
            "-980+(980*(t-0.20)/0.65),0))'"
            ":"
            "y='170+5*sin(t*1.2)'"
            ":eof_action=pass"
            "[v1]"
        ),

        (
            "[v1]"
            "[hook]"
            "overlay="
            f"x='if(lt(t,{hook_start:.3f}),1080,"
            f"if(lt(t,{hook_start + 0.65:.3f}),"
            f"1080-(1080*(t-{hook_start:.3f})/0.65),80))'"
            ":"
            "y='730+4*cos(t*1.1)'"
            ":eof_action=pass"
            "[v2]"
        ),

        (
            "[v2]"
            "[take]"
            "overlay="
            f"x='80+4*sin(t*0.9)':"
            f"y='if(lt(t,{take_start:.3f}),"
            f"1980,"
            f"if(lt(t,{take_start + 0.70:.3f}),"
            f"1980-(1980*0.70*(t-{take_start:.3f})/0.70),"
            f"1030))'"
            ":eof_action=pass"
            "[v3]"
        ),

        (
            "[v3]"
            "[source]"
            f"overlay="
            f"x='80':"
            f"y='1740+3*sin(t*1.4)'"
            ":eof_action=pass"
            "[v4]"
        ),
    ]

    filter_complex = ";".join(filters)

    audio_index = 5

    command = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[v4]",
        "-map",
        f"{audio_index}:a",
        "-t",
        str(duration),
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_video),
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(
            exc.stderr[-10000:],
            flush=True,
        )

        raise RuntimeError(
            "FFmpeg failed to create the Phase 3 professional animated Short."
        ) from exc

    if not out_video.exists():
        raise RuntimeError(
            "FFmpeg finished but video was not created."
        )

    if out_video.stat().st_size == 0:
        raise RuntimeError(
            "FFmpeg created an empty video."
        )

    print(
        f"Phase 3 professional animated Short created: {out_video}",
        flush=True,
    )

    return out_video