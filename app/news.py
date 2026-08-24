from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import requests


@dataclass
class Story:
    title: str
    url: str
    source: str
    published: datetime
    summary: str


FEEDS = [
    ("Google News AI", "artificial intelligence AI when:1d"),
    ("Google News OpenAI", "OpenAI when:1d"),
    ("Google News Gemini", "Google Gemini when:1d"),
    ("Google News Anthropic", "Anthropic Claude when:1d"),
    ("Google News Nvidia AI", "NVIDIA AI when:1d"),
]


def _feed_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )


def _published(entry):
    for key in ("published", "updated"):
        value = entry.get(key)

        if value:
            try:
                return parsedate_to_datetime(value).astimezone(timezone.utc)
            except Exception:
                pass

    return datetime.now(timezone.utc)


def _source(entry, fallback):
    source = entry.get("source")

    if isinstance(source, dict):
        return source.get("title") or fallback

    return str(source) if source else fallback


def _clean(text):
    return " ".join((text or "").split())


def fetch_stories(lookback_hours=30):
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=lookback_hours
    )

    stories = []

    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0 AI-News-Shorts-Agent/1.0",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })

    print(
        f"Checking {len(FEEDS)} news feeds...",
        flush=True
    )

    for index, (feed_name, query) in enumerate(FEEDS, start=1):

        print(
            f"[{index}/{len(FEEDS)}] {feed_name} ...",
            flush=True
        )

        url = _feed_url(query)

        try:

            response = session.get(
                url,
                timeout=(5, 15)
            )

            response.raise_for_status()

            if not response.content:
                print(
                    "EMPTY RESPONSE - skipped",
                    flush=True
                )
                continue

            parsed = feedparser.parse(
                response.content
            )

            if not parsed.entries:
                print(
                    "NO STORIES - skipped",
                    flush=True
                )
                continue

            count = 0

            for entry in parsed.entries:

                published = _published(entry)

                if published < cutoff:
                    continue

                title = _clean(
                    entry.get("title", "")
                )

                link = entry.get(
                    "link",
                    ""
                )

                summary = _clean(
                    entry.get("summary", "")
                )

                if title and link:

                    stories.append(
                        Story(
                            title=title,
                            url=link,
                            source=_source(
                                entry,
                                feed_name
                            ),
                            published=published,
                            summary=summary[:1000],
                        )
                    )

                    count += 1

            print(
                f"OK ({count} fresh stories)",
                flush=True
            )

        except requests.Timeout:

            print(
                "TIMEOUT - skipped",
                flush=True
            )

        except requests.RequestException as exc:

            print(
                f"HTTP ERROR - {exc}",
                flush=True
            )

        except Exception as exc:

            print(
                f"ERROR - {type(exc).__name__}: {exc}",
                flush=True
            )

    # Remove duplicate stories
    seen = set()
    unique = []

    for story in sorted(
        stories,
        key=lambda x: x.published,
        reverse=True
    ):

        key = hashlib.sha1(
            story.title.lower().encode("utf-8")
        ).hexdigest()

        if key not in seen:

            seen.add(key)
            unique.append(story)

    print(
        f"Total unique fresh stories: {len(unique)}",
        flush=True
    )

    if not unique:

        raise RuntimeError(
            "No fresh AI stories were retrieved."
        )

    return unique


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "how", "i", "in", "is", "it", "its", "of", "on",
    "or", "that", "the", "this", "to", "was", "were", "what",
    "when", "where", "which", "who", "why", "with", "you",
    "your", "about", "important", "importance",
}


_TOPIC_ALIASES = {
    "genai": [
        "genai",
        "generative ai",
        "generative artificial intelligence",
    ],
    "generative ai": [
        "genai",
        "generative ai",
        "generative artificial intelligence",
    ],
    "ai agents": [
        "ai agent",
        "ai agents",
        "agentic ai",
        "agentic",
        "autonomous agent",
        "autonomous agents",
    ],
    "ai agent": [
        "ai agent",
        "ai agents",
        "agentic ai",
        "agentic",
    ],
    "openai": ["openai", "chatgpt", "gpt"],
    "gemini": ["google gemini", "gemini", "google deepmind"],
    "anthropic": ["anthropic", "claude"],
    "nvidia": ["nvidia", "cuda", "blackwell"],
    "robotics": ["robot", "robotics", "humanoid"],
    "ai-business": [
        "ai business", "enterprise ai", "ai company",
        "ai investment", "ai funding",
    ],
    "ai-research": [
        "ai research", "research", "paper", "model", "benchmark",
    ],
    "ai-tools": [
        "ai tool", "ai tools", "ai app", "ai software",
    ],
}


def _topic_terms(topic: str) -> list[str]:
    """Turn a natural-language custom topic into useful concepts."""
    normalized = _clean(topic).lower()

    if not normalized:
        return []

    terms = []

    for alias, expansions in _TOPIC_ALIASES.items():
        if alias in normalized:
            terms.extend(expansions)

    words = re.findall(
        r"[a-z0-9]+(?:[-'][a-z0-9]+)*",
        normalized,
    )

    for word in words:
        if len(word) < 3 or word in _STOP_WORDS:
            continue
        terms.append(word)

    result = []
    for term in terms:
        term = term.strip().lower()
        if term and term not in result:
            result.append(term)

    return result


def _topic_relevance(
    story: Story,
    terms: list[str],
) -> tuple[int, int]:
    """Score a story against topic concepts."""
    title = story.title.lower()
    summary = story.summary.lower()
    source = story.source.lower()

    score = 0
    matched = set()

    for term in terms:
        if term in title:
            score += 12
            matched.add(term)
        elif term in summary:
            score += 5
            matched.add(term)
        elif term in source:
            score += 3
            matched.add(term)

    if len(matched) >= 2:
        score += 8
    if len(matched) >= 3:
        score += 8

    return score, len(matched)


def rank_stories(
    stories,
    limit=3,
    topic=None,
):
    now = datetime.now(timezone.utc)

    normalized_topic = (
        str(topic).strip().lower()
        if topic
        else ""
    )

    generic_topics = {
        "",
        "top-ai-news",
    }

    # --------------------------------------------------------
    # GENERIC AI NEWS
    # --------------------------------------------------------

    if normalized_topic in generic_topics:

        def score(story):
            age_hours = max(
                0,
                (
                    now - story.published
                ).total_seconds() / 3600,
            )

            recency = max(
                0,
                24 - age_hours,
            )

            source_bonus = 2 if any(
                keyword in story.source.lower()
                for keyword in [
                    "reuters",
                    "associated press",
                    "ap news",
                    "bloomberg",
                    "techcrunch",
                    "the verge",
                ]
            ) else 0

            return recency + source_bonus

        return sorted(
            stories,
            key=score,
            reverse=True,
        )[:max(limit * 5, 15)]

    # --------------------------------------------------------
    # CUSTOM / TOPIC-SPECIFIC NEWS
    # --------------------------------------------------------

    terms = _topic_terms(
        normalized_topic
    )

    print(
        f"Topic concepts: {', '.join(terms) or '(none)'}",
        flush=True,
    )

    if not terms:
        raise RuntimeError(
            f"Unable to extract meaningful concepts from "
            f"custom topic: '{topic}'."
        )

    scored = []

    for story in stories:

        relevance, matched_count = _topic_relevance(
            story,
            terms,
        )

        if relevance <= 0:
            continue

        age_hours = max(
            0,
            (
                now - story.published
            ).total_seconds() / 3600,
        )

        recency = max(
            0,
            24 - age_hours,
        )

        source_bonus = 2 if any(
            keyword in story.source.lower()
            for keyword in [
                "reuters",
                "associated press",
                "ap news",
                "bloomberg",
                "techcrunch",
                "the verge",
            ]
        ) else 0

        # Topic relevance is deliberately dominant.
        total_score = (
            relevance * 10
            + matched_count * 8
            + recency
            + source_bonus
        )

        scored.append(
            (
                total_score,
                relevance,
                matched_count,
                story,
            )
        )

    if not scored:
        raise RuntimeError(
            f"No sufficiently relevant news stories found "
            f"for custom topic: '{topic}'."
        )

    scored.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2],
            item[3].published,
        ),
        reverse=True,
    )

    selected = [
        item[3]
        for item in scored[:max(limit * 5, 15)]
    ]

    print(
        f"Topic-relevant stories: {len(scored)}",
        flush=True,
    )

    print(
        "Top topic matches:",
        flush=True,
    )

    for index, (
        total_score,
        relevance,
        matched_count,
        story,
    ) in enumerate(
        scored[:min(5, len(scored))],
        start=1,
    ):
        print(
            f"  [{index}] score={total_score}, "
            f"matches={matched_count}, "
            f"title={story.title}",
            flush=True,
        )

    return selected
