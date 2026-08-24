from __future__ import annotations

import json
import re
import time
from typing import Any

from openai import OpenAI

from .news import Story


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM = """
You are the editorial director for a professional AI-news
YouTube Shorts channel.

Your job is to select the most important AI news story from
the supplied candidates and create a short, accurate,
human-sounding YouTube Short.

CORE RULES
----------

1. Never invent facts.

2. Only use information supported by the supplied candidate
   title, source, summary, URL and publication information.

3. Do not fabricate numbers, quotes, product capabilities,
   company statements or events.

4. Prefer meaningful AI developments such as:
   - major model releases
   - important product launches
   - AI research
   - major company announcements
   - AI infrastructure
   - robotics
   - funding
   - regulation
   - safety incidents
   - major enterprise AI deployments

5. Prefer credible and authoritative sources when the supplied
   candidates allow it.

6. Avoid sensational clickbait.

7. The final Short should sound like a knowledgeable human
   technology presenter speaking directly to viewers.

VOICEOVER STYLE
---------------

The voiceover is written for SPOKEN YouTube Shorts.

It must NOT sound like a newspaper article, corporate press
release or AI-generated essay.

Use:

- natural conversational language in the requested language
- short sentences
- contractions such as "it's", "that's", "don't", "you'll"
- simple spoken vocabulary
- natural transitions
- occasional conversational phrases such as:
  "Here's the interesting part."
  "And this is why it matters."
  "The big takeaway?"
  "So, what's going on?"
  "That could be a big deal."
- a strong opening
- clear pacing
- natural sentence rhythm

Avoid:

- "This development marks a significant step..."
- "In a significant development..."
- "According to reports..." unless actually necessary
- corporate/academic language
- repetitive phrases
- unnecessary explanations
- exaggerated claims
- fake excitement
- phrases that sound like an AI reading an article

The narration should sound like a real technology YouTuber
explaining the story to another person.

Target voiceover length:
20-30 seconds.

The hook should immediately tell the viewer why they should
care about the story.

VISUAL TEXT LANGUAGE RULES
--------------------------

The video has TWO completely separate language layers:

1. ON-SCREEN / VISUAL TEXT
2. VOICEOVER / AUDIO

ON-SCREEN / VISUAL TEXT MUST ALWAYS BE IN ENGLISH.

The following fields MUST ALWAYS use English text:
- hook
- headline
- visual_concept
- key_takeaways
- youtube_title
- description
- hashtags

Do NOT write visual fields in Hindi, Devanagari, Hinglish,
Arabic, Cyrillic, Chinese, Japanese, Bengali, or any other
non-English script.

VOICEOVER IS THE ONLY FIELD THAT FOLLOWS THE USER'S
SELECTED AUDIO LANGUAGE.

If the selected audio language is:
- English: write the voiceover in natural English.
- Hindi: write the voiceover in natural Hindi using Devanagari.
- Hinglish: write the voiceover in natural Indian Hinglish
  using Roman/Latin script.

IMPORTANT EXAMPLE:

Selected audio language: Hindi

CORRECT:
headline:
"Anthropic Expands Claude AI in Europe"

key_takeaways:
[
  "Anthropic is expanding Claude AI availability in Europe.",
  "The expansion increases access across EU markets.",
  "The move comes as European AI regulation evolves."
]

voiceover:
"Anthropic ने Europe में Claude AI को लेकर एक बड़ा कदम उठाया है..."

INCORRECT:
headline:
"Anthropic ने Europe में Claude AI को लेकर बड़ा कदम उठाया"

The headline must remain English even when the voiceover is Hindi.

Never translate visual text into the selected audio language.
Never translate the voiceover into English just to satisfy the
visual-text requirement.

"""


# ============================================================
# JSON EXTRACTION
# ============================================================


def extract_json(text: str) -> dict:
    """
    Extract JSON safely from an OpenRouter response.

    Handles:
    - normal JSON
    - ```json fenced JSON
    - ``` fenced JSON
    - surrounding text
    """

    if not text:
        raise RuntimeError(
            "OpenRouter returned an empty response."
        )

    text = text.strip()

    # --------------------------------------------------------
    # Remove markdown fences
    # --------------------------------------------------------

    if text.startswith("```json"):
        text = text[
            len("```json"):
        ].strip()

    elif text.startswith("```"):
        text = text[
            len("```"):
        ].strip()

    if text.endswith("```"):
        text = text[
            :-3
        ].strip()

    # --------------------------------------------------------
    # First attempt: direct JSON
    # --------------------------------------------------------

    try:
        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Second attempt: locate JSON object
    # --------------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        candidate = text[
            start:end + 1
        ]

        try:
            result = json.loads(
                candidate
            )

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError as exc:

            raise RuntimeError(
                "Invalid JSON: "
                f"{exc}\n\n"
                f"Response:\n{text}"
            ) from exc

    raise RuntimeError(
        "OpenRouter did not return a valid JSON object.\n\n"
        f"Response:\n{text}"
    )


# ============================================================
# NORMALIZE TEXT
# ============================================================


def _clean_text(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# VALIDATE STORY NUMBER
# ============================================================


def _validate_story_number(
    value: Any,
    maximum: int,
    field_name: str,
) -> int:

    # bool is technically an int in Python, but must not be
    # accepted as a story number.
    if isinstance(value, bool):
        raise RuntimeError(
            f"{field_name} must be an integer."
        )

    if not isinstance(value, int):
        raise RuntimeError(
            f"{field_name} is missing or invalid."
        )

    if not (
        1 <= value <= maximum
    ):
        raise RuntimeError(
            f"Invalid {field_name}: {value}"
        )

    return value


# ============================================================
# VALIDATE VISUAL TEXT LANGUAGE
# ============================================================

# Visual/on-screen text is English-only.
# These ranges catch common non-Latin scripts while allowing
# normal English punctuation, numbers, URLs, apostrophes, etc.
NON_ENGLISH_SCRIPT_RE = re.compile(
    r"[\u0400-\u052F"      # Cyrillic
    r"\u0590-\u05FF"       # Hebrew
    r"\u0600-\u06FF"       # Arabic
    r"\u0900-\u097F"       # Devanagari
    r"\u0980-\u09FF"       # Bengali
    r"\u0A00-\u0A7F"       # Gurmukhi
    r"\u0A80-\u0AFF"       # Gujarati
    r"\u0B00-\u0B7F"       # Oriya
    r"\u0B80-\u0BFF"       # Tamil
    r"\u0C00-\u0C7F"       # Telugu
    r"\u0C80-\u0CFF"       # Kannada
    r"\u0D00-\u0D7F"       # Malayalam
    r"\u0E00-\u0E7F"       # Thai
    r"\u1100-\u11FF"       # Hangul Jamo
    r"\u3040-\u30FF"       # Japanese
    r"\u3400-\u4DBF"       # CJK Extension A
    r"\u4E00-\u9FFF"       # CJK
    r"\uAC00-\uD7AF"       # Hangul
    r"]"
)


def _validate_english_visual_text(
    field_name: str,
    value: str,
) -> str:
    value = _clean_text(value)

    if not value:
        raise RuntimeError(
            f"Visual field '{field_name}' is empty."
        )

    if NON_ENGLISH_SCRIPT_RE.search(value):
        raise RuntimeError(
            f"Visual field '{field_name}' contains "
            "non-English/non-Latin characters. "
            "On-screen text must always be English. "
            "Only the voiceover may use the selected "
            "audio language."
        )

    return value


# ============================================================

def validate_editorial(
    result: dict,
    candidates: list[Story],
) -> dict:

    if not isinstance(result, dict):
        raise RuntimeError(
            "Editorial response is not a JSON object."
        )

    if not candidates:
        raise RuntimeError(
            "No candidates were supplied to editorial AI."
        )

    # --------------------------------------------------------
    # TOP 3
    # --------------------------------------------------------

    top3 = result.get(
        "top3"
    )

    if not isinstance(top3, list):
        raise RuntimeError(
            "Editorial response does not contain a valid top3 list."
        )

    if len(top3) < 3:
        raise RuntimeError(
            "Editorial response must contain at least 3 top3 stories."
        )

    selected_numbers = set()

    validated_top3 = []

    for index, item in enumerate(
        top3[:3],
        start=1,
    ):

        if not isinstance(item, dict):
            raise RuntimeError(
                f"top3 item {index} is invalid."
            )

        story_number = _validate_story_number(
            item.get(
                "story_number"
            ),
            len(candidates),
            f"top3 item {index} story_number",
        )

        if story_number in selected_numbers:
            raise RuntimeError(
                f"Duplicate story selected: "
                f"{story_number}"
            )

        selected_numbers.add(
            story_number
        )

        why_it_matters = _clean_text(
            item.get(
                "why_it_matters"
            )
        )

        if not why_it_matters:
            raise RuntimeError(
                f"top3 item {index} has no why_it_matters."
            )

        validated_top3.append(
            {
                "story_number": story_number,
                "why_it_matters": (
                    why_it_matters
                ),
            }
        )

    # --------------------------------------------------------
    # LEAD STORY NUMBER
    # --------------------------------------------------------

    lead_story_number = _validate_story_number(
        result.get(
            "lead_story_number"
        ),
        len(candidates),
        "lead_story_number",
    )

    if (
        lead_story_number
        not in selected_numbers
    ):
        raise RuntimeError(
            "lead_story_number must be one of the selected top3 stories."
        )

    # --------------------------------------------------------
    # LEAD OBJECT
    # --------------------------------------------------------

    lead = result.get(
        "lead"
    )

    if not isinstance(
        lead,
        dict,
    ):
        raise RuntimeError(
            "Editorial does not contain a valid lead object."
        )

    required_fields = [
        "hook",
        "headline",
        "visual_concept",
        "key_takeaways",
        "voiceover",
        "youtube_title",
        "description",
        "hashtags",
    ]

    for field in required_fields:

        if field not in lead:
            raise RuntimeError(
                f"Lead is missing required field: {field}"
            )

    hook = _clean_text(
        lead.get("hook")
    )

    headline = _clean_text(
        lead.get("headline")
    )

    visual_concept = _clean_text(
        lead.get("visual_concept")
    )

    key_takeaways = lead.get(
        "key_takeaways"
    )

    voiceover = _clean_text(
        lead.get("voiceover")
    )

    youtube_title = _clean_text(
        lead.get("youtube_title")
    )

    description = _clean_text(
        lead.get("description")
    )

    hashtags = lead.get(
        "hashtags"
    )

    if not hook:
        raise RuntimeError(
            "Lead hook is empty."
        )

    if not headline:
        raise RuntimeError(
            "Lead headline is empty."
        )

    if not visual_concept:
        raise RuntimeError(
            "Lead visual_concept is empty."
        )

    if not voiceover:
        raise RuntimeError(
            "Lead voiceover is empty."
        )

    if not youtube_title:
        raise RuntimeError(
            "Lead youtube_title is empty."
        )

    if not description:
        raise RuntimeError(
            "Lead description is empty."
        )

    if not isinstance(
        hashtags,
        list,
    ):
        raise RuntimeError(
            "Lead hashtags must be a list."
        )

    if not isinstance(
        key_takeaways,
        list,
    ):
        raise RuntimeError(
            "Lead key_takeaways must be a list."
        )

    if len(key_takeaways) < 2:
        raise RuntimeError(
            "Lead key_takeaways must contain at least 2 items."
        )

    key_takeaways = [
        _validate_english_visual_text(
            "key_takeaway",
            item,
        )
        for item in key_takeaways[:3]
    ]

    # Visual fields are ALWAYS English.
    # Voiceover is intentionally excluded because it follows
    # the selected audio language.
    hook = _validate_english_visual_text(
        "hook",
        hook,
    )

    headline = _validate_english_visual_text(
        "headline",
        headline,
    )

    visual_concept = _validate_english_visual_text(
        "visual_concept",
        visual_concept,
    )

    youtube_title = _validate_english_visual_text(
        "youtube_title",
        youtube_title,
    )

    description = _validate_english_visual_text(
        "description",
        description,
    )

    clean_hashtags = []

    for tag in hashtags:

        tag = _clean_text(
            tag
        )

        if not tag:
            continue

        if not tag.startswith("#"):
            tag = "#" + tag

        clean_hashtags.append(
            tag
        )

    if not clean_hashtags:
        clean_hashtags = [
            "#AI",
            "#ArtificialIntelligence",
            "#TechNews",
            "#Shorts",
        ]

    # --------------------------------------------------------
    # Limit YouTube title
    # --------------------------------------------------------

    youtube_title = (
        youtube_title[:90]
    )

    # --------------------------------------------------------
    # Return normalized structure
    # --------------------------------------------------------

    return {
        "top3": validated_top3,
        "lead_story_number": lead_story_number,
        "lead": {
            "hook": hook,
            "headline": headline,
            "visual_concept": visual_concept,
            "key_takeaways": key_takeaways,
            "voiceover": voiceover,
            "youtube_title": youtube_title,
            "description": description,
            "hashtags": clean_hashtags,
        },
    }


# ============================================================
# BUILD CANDIDATE PAYLOAD
# ============================================================


def build_candidate_payload(
    candidates: list[Story],
) -> list[dict]:

    payload = []

    for number, story in enumerate(
        candidates,
        start=1,
    ):

        payload.append(
            {
                "story_number": number,
                "title": story.title,
                "source": story.source,
                "published": (
                    story.published.isoformat()
                ),
                "url": story.url,
                "summary": story.summary,
            }
        )

    return payload


# ============================================================
# BUILD EDITORIAL PROMPT
# ============================================================


def build_prompt(
    candidates: list[Story],
    language: str = "english",
    tone: str = "natural",
    topic: str = "",
) -> str:

    payload = build_candidate_payload(
        candidates
    )

    language_instruction = {
        "english": "Write the voiceover entirely in natural English.",
        "hindi": "Write the voiceover entirely in natural Hindi using Devanagari script.",
        "hinglish": "Write the voiceover in natural Indian Hinglish using Roman/Latin script.",
    }.get(
        language.lower(),
        f"Write the voiceover in {language}.",
    )

    tone_instruction = {
        "natural": "Natural, conversational and human.",
        "professional": "Professional, clear and authoritative.",
        "energetic": "Energetic, engaging and fast-paced.",
        "breaking-news": "Breaking-news style: urgent, concise and direct.",
    }.get(
        tone.lower(),
        f"Use a {tone} narration tone.",
    )

    return f"""
Here are the candidate AI news stories.

CANDIDATES
==========

{json.dumps(
    payload,
    ensure_ascii=False,
    indent=2,
)}

USER SETTINGS
=============

Requested topic:
{topic}

Requested narration language:
{language}

LANGUAGE INSTRUCTION:
{language_instruction}

Requested narration tone:
{tone}

TONE INSTRUCTION:
{tone_instruction}

These settings are mandatory.

LANGUAGE SEPARATION IS CRITICAL:

The requested narration language applies ONLY to the "voiceover"
field.

All visual/on-screen fields MUST remain in English:
- hook
- headline
- visual_concept
- key_takeaways
- youtube_title
- description
- hashtags

If the requested narration language is Hindi, ONLY "voiceover"
should be Hindi. Do not translate the headline, hook, visual
concept, key takeaways, title, description, or hashtags.

If the requested narration language is Hinglish, ONLY "voiceover"
may use Hinglish. Keep every visual field in English.

The topic is mandatory: keep the editorial selection and
voiceover focused on the requested topic when the candidates support it.

The narration tone applies to the voiceover only.

EDITORIAL TASK
==============

Select the three most consequential stories.

Use the supplied story_number values.

Then select ONE of those three as the lead story.

IMPORTANT:

The lead_story_number MUST match one of the selected
top3 story_number values.

Do not invent URLs.

Do not create a story that is not present in the candidates.

Do not use facts that are not supported by the supplied
candidate information.

VOICEOVER REQUIREMENTS
======================

Write a 20-30 second spoken narration.

It should sound like a real human technology presenter.

BAD STYLE:

"OpenAI's latest development represents a significant
milestone in the rapidly evolving artificial intelligence
landscape."

GOOD STYLE:

"OpenAI just made a pretty interesting move. Here's what
happened, and why it matters."

Use natural spoken language.

Prefer:

"It's"
"That's"
"Here's"
"What's happening"
"Why does this matter?"
"The big takeaway"

Avoid:

"This development marks..."
"In a significant development..."
"Furthermore..."
"Moreover..."
"Consequently..."
"According to reports..." unless necessary
"industry observers believe..." unless supplied
"this represents a major milestone..." unless actually
supported by the source

Do not make the narration sound like a press release.

The first sentence should create curiosity.

The narration must remain factually grounded.

VISUAL REQUIREMENTS
===================

The visual_concept is used by the text-based news graphic
pipeline.

Describe what information should appear visually.

IMPORTANT:
All visual/on-screen text MUST be English.

The following must ALWAYS be English:
- hook
- headline
- visual_concept
- key_takeaways
- youtube_title
- description
- hashtags

Do NOT use Hindi, Devanagari, Arabic, Cyrillic, Chinese,
Japanese, Bengali, or any other non-English script in those fields.

Do NOT require a photorealistic AI-generated image.

Do NOT depend on text being generated inside an AI image.

Keep the concept suitable for a vertical 9:16 news graphic.

YOUTUBE TITLE
=============

Maximum 90 characters.

Make it interesting but not misleading.

DESCRIPTION
===========

Keep it short.

Mention the actual source.

HASHTAGS
========

Use relevant hashtags.

Return ONLY valid JSON.

EXACT JSON SHAPE
================

{{
  "top3": [
    {{
      "story_number": 1,
      "why_it_matters": "One concise factual sentence."
    }},
    {{
      "story_number": 2,
      "why_it_matters": "One concise factual sentence."
    }},
    {{
      "story_number": 3,
      "why_it_matters": "One concise factual sentence."
    }}
  ],
  "lead_story_number": 1,
  "lead": {{
    "hook": "Short English hook for the on-screen graphic.",
    "headline": "Short English headline for the on-screen graphic.",
    "visual_concept": "English description for a vertical text-based news graphic.",
    "key_takeaways": [
      "Short English takeaway 1.",
      "Short English takeaway 2.",
      "Short English takeaway 3."
    ],
    "voiceover": "Natural 20-30 second human-sounding narration in the requested audio language.",
    "youtube_title": "YouTube title under 90 characters.",
    "description": "Short description with source attribution.",
    "hashtags": [
      "#AI",
      "#ArtificialIntelligence",
      "#TechNews",
      "#Shorts"
    ]
  }}
}}
"""


# ============================================================
# OPENROUTER REQUEST
# ============================================================


def _call_openrouter(
    client: OpenAI,
    model: str,
    prompt: str,
    attempt: int,
) -> str:

    print(
        f"OpenRouter attempt {attempt}/2...",
        flush=True,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
        max_tokens=6000,
        response_format={
            "type": "json_object"
        },
        timeout=60,
    )

    # --------------------------------------------------------
    # Validate choices
    # --------------------------------------------------------

    if not response.choices:

        raise RuntimeError(
            "OpenRouter returned no choices."
        )

    choice = response.choices[0]

    # --------------------------------------------------------
    # Content
    # --------------------------------------------------------

    content = getattr(
        choice.message,
        "content",
        None,
    )

    # --------------------------------------------------------
    # Some reasoning models may return no visible content
    # if the completion budget is consumed by reasoning.
    # --------------------------------------------------------

    if content is None:

        reasoning = getattr(
            choice.message,
            "reasoning",
            None,
        )

        finish_reason = getattr(
            choice,
            "finish_reason",
            None,
        )

        raise RuntimeError(
            "OpenRouter returned no message content. "
            f"finish_reason={finish_reason}; "
            f"reasoning_present={bool(reasoning)}"
        )

    content = str(
        content
    ).strip()

    if not content:

        raise RuntimeError(
            "OpenRouter returned empty message content."
        )

    # Some reasoning/provider combinations can occasionally return a
    # syntactically valid but empty JSON object. That is not a usable
    # editorial response, so force the normal retry path instead of
    # allowing validation to fail with the less useful top3 error.
    if content in ("{}", "null", "[]"):
        finish_reason = getattr(
            choice,
            "finish_reason",
            None,
        )
        reasoning = getattr(
            choice.message,
            "reasoning",
            None,
        )
        raise RuntimeError(
            "OpenRouter returned an empty JSON structure. "
            f"finish_reason={finish_reason}; "
            f"reasoning_present={bool(reasoning)}"
        )

    print(
        "OpenRouter connected. Receiving response:",
        flush=True,
    )

    print(
        content,
        flush=True,
    )

    print(
        "OpenRouter response complete.",
        flush=True,
    )

    print(
        f"Response length: {len(content)}",
        flush=True,
    )

    return content


# ============================================================
# BUILD EDITORIAL
# ============================================================


def build_editorial(
    client: OpenAI,
    candidates: list[Story],
    model: str,
    provider: str = "openai",
    language: str = "english",
    tone: str = "natural",
    topic: str = "",
) -> dict:

    if not candidates:
        raise RuntimeError(
            "No candidate stories supplied."
        )

    if provider != "openrouter":
        raise RuntimeError(
            "This editor is configured for OpenRouter. "
            f"Received provider: {provider}"
        )

    # --------------------------------------------------------
    # Keep the request reasonably small.
    #
    # The main application normally sends 5 candidates.
    # --------------------------------------------------------

    candidates = candidates[:5]

    prompt = build_prompt(
        candidates=candidates,
        language=language,
        tone=tone,
        topic=topic,
    )

    last_error = None

    # --------------------------------------------------------
    # Two attempts.
    #
    # This protects the daily automation from temporary
    # OpenRouter/provider failures.
    # --------------------------------------------------------

    for attempt in range(
        1,
        3,
    ):

        try:

            request_prompt = prompt

            if attempt == 2:
                request_prompt = (
                    prompt
                    + "\n\nFINAL CORRECTION BEFORE RETRY\n"
                    + "================================\n"
                    + "The previous attempt did not produce a complete "
                      "valid editorial JSON object.\n"
                    + "RETURN THE FULL JSON OBJECT NOW. Do not return {}, "
                      "null, [], or an empty response.\n"
                    + "You MUST include top3 with exactly 3 stories, "
                      "lead_story_number, and the complete lead object.\n"
                    + "Verify every visual field is English before "
                      "returning JSON.\n"
                    + "Visual fields: hook, headline, visual_concept, "
                      "key_takeaways, youtube_title, description, "
                      "hashtags.\n"
                    + "Only voiceover may use the requested audio "
                      "language.\n"
                    + "Do NOT translate visual fields into Hindi or "
                      "any other selected audio language.\n"
                )

            text = _call_openrouter(
                client=client,
                model=model,
                prompt=request_prompt,
                attempt=attempt,
            )

            result = extract_json(
                text
            )

            result = validate_editorial(
                result,
                candidates,
            )
            
            print(
                "VALIDATED HEADLINE:",
                result["lead"]["headline"],
                flush=True,
            )

            print(
                "VALIDATED HOOK:",
                result["lead"]["hook"],
                flush=True,
)

            # ------------------------------------------------
            # Resolve actual story metadata.
            #
            # The model returns story_number rather than
            # inventing URLs/source names.
            # ------------------------------------------------

            resolved_top3 = []

            for item in result[
                "top3"
            ]:

                story_number = item[
                    "story_number"
                ]

                story = candidates[
                    story_number - 1
                ]

                resolved_top3.append(
                    {
                        "story_number": story_number,
                        "title": story.title,
                        "source": story.source,
                        "url": story.url,
                        "published": (
                            story.published.isoformat()
                        ),
                        "why_it_matters": item[
                            "why_it_matters"
                        ],
                    }
                )

            result[
                "top3"
            ] = resolved_top3

            # ------------------------------------------------
            # Resolve lead story metadata.
            # ------------------------------------------------

            lead_story_number = result[
                "lead_story_number"
            ]

            lead_story = candidates[
                lead_story_number - 1
            ]

            # ------------------------------------------------
            # Add source information to lead.
            #
            # This is useful to main.py for:
            #
            # - source display
            # - YouTube description
            # - logging
            # ------------------------------------------------

            result[
                "lead"
            ][
                "source"
            ] = lead_story.source

            result[
                "lead"
            ][
                "url"
            ] = lead_story.url

            result[
                "lead"
            ][
                "published"
            ] = lead_story.published.isoformat()

            print(
                "Editorial generated successfully.",
                flush=True,
            )

            print(
                "Lead story: "
                f"{lead_story.title} - "
                f"{lead_story.source}",
                flush=True,
            )

            print(
                "Lead URL: "
                f"{lead_story.url}",
                flush=True,
            )

            return result

        except Exception as exc:

            last_error = exc

            print(
                f"OpenRouter attempt {attempt} failed: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

            # ------------------------------------------------
            # Retry only after the first attempt.
            # ------------------------------------------------

            if attempt < 2:

                print(
                    "Retrying OpenRouter in 3 seconds...",
                    flush=True,
                )

                time.sleep(
                    3
                )

    # --------------------------------------------------------
    # Both attempts failed.
    # --------------------------------------------------------

    raise RuntimeError(
        "OpenRouter editorial generation failed "
        "after 2 attempts: "
        f"{type(last_error).__name__}: {last_error}"
    )