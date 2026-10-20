"""Caption intelligence (roadmap 12.3): keyword emphasis.

Picks the most "important" words in a caption line (using purely deterministic
heuristics — stopword list, length, ALL-CAPS and digits) and wraps them in ASS
override tags so they render larger and in an accent colour. Kept separate from
``captions.py`` (serialisation) so the text scoring has no dependency on the
caption dataclasses and stays trivially unit-testable.
"""

from __future__ import annotations

import re

# Function words and other low-information tokens that never get emphasis.
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "him",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "just",
        "like",
        "me",
        "my",
        "no",
        "not",
        "of",
        "on",
        "or",
        "our",
        "out",
        "she",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "up",
        "us",
        "was",
        "we",
        "were",
        "what",
        "when",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
        "your",
    }
)

_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _score(token: str, *, min_length: int) -> int | None:
    """Importance score for a token, or ``None`` when it is not eligible."""
    lowered = token.lower()
    if len(token) < min_length or lowered in STOPWORDS:
        return None
    score = 0
    if token.isupper() and len(token) > 1:
        score += 2
    if any(char.isdigit() for char in token):
        score += 2
    if len(token) >= min_length + 3:
        score += 1
    return score


def detect_emphasis(text: str, *, min_length: int = 4, limit: int = 2) -> list[str]:
    """Return up to ``limit`` emphasis words from ``text``, best first.

    Ties resolve to first appearance so the choice is deterministic. Repeated
    words are emphasised once.
    """
    scored: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for position, token in enumerate(_WORD_RE.findall(text)):
        score = _score(token, min_length=min_length)
        if score is None:
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        scored.append((score, position, token))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [token for _, _, token in scored[: max(limit, 0)]]


def emphasize_text(text: str, words: list[str], *, color: str, scale: int, reset_color: str) -> str:
    """Wrap whole-word matches of ``words`` in ASS override tags.

    The emphasis tags are closed again with ``reset_color``/100% scale so only
    the matched word is affected.
    """
    unique = sorted({word for word in words if word}, key=len, reverse=True)
    if not unique:
        return text
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(word) for word in unique) + r")\b", re.IGNORECASE
    )
    opening = f"{{\\c{color}\\fscx{scale}\\fscy{scale}}}"
    closing = f"{{\\c{reset_color}\\fscx100\\fscy100}}"
    return pattern.sub(lambda match: f"{opening}{match.group(0)}{closing}", text)
