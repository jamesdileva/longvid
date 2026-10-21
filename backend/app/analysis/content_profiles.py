"""Content profiles (roadmap Phase 13).

A content profile specializes highlight detection for a kind of source video.
It carries two things:

* **Prompt guidance** — the kinds of moments the LLM should look for (kills and
  clutches for gaming, strong opinions and stories for podcasts, ...).
* **A deterministic keyword lexicon** — so profile-specific moments can also be
  surfaced without an LLM, and so model judgments can be nudged by concrete
  signals in the transcript.

Profiles are pure data shared by the API, candidate pipeline and tests.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

DEFAULT_CONTENT_PROFILE_KEY = "general"


class UnknownContentProfileError(ValueError):
    """Raised when a content profile key is not in the catalog."""


@dataclass(frozen=True)
class ContentProfile:
    """A specialized analysis profile."""

    key: str
    label: str
    description: str
    guidance: str
    keywords: tuple[str, ...] = ()
    category: str = "highlight"

    def keyword_hits(self, text: str) -> int:
        """Count distinct lexicon words present in ``text`` (whole words)."""
        if not self.keywords or not text:
            return 0
        lowered = text.lower()
        return sum(
            1 for keyword in self.keywords if re.search(rf"\b{re.escape(keyword)}\b", lowered)
        )

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of the profile."""
        data = asdict(self)
        data["keywords"] = list(self.keywords)
        return data


_PROFILES: tuple[ContentProfile, ...] = (
    ContentProfile(
        key="general",
        label="General",
        description="Broad semantic scoring with no specialized focus.",
        guidance=(
            "Score broadly for any moment that stands on its own: a clear idea, "
            "an emotional beat, a surprising statement, or a self-contained story."
        ),
    ),
    ContentProfile(
        key="gaming",
        label="Gaming",
        description="Kills, wins and losses, boss fights, reactions, clutches and fails.",
        guidance=(
            "Prioritize gameplay highlights: kills, wins and losses, boss kills, "
            "clutches, fails, and the genuine reactions that follow them. A clip "
            "should usually include the build-up action and the immediate reaction."
        ),
        keywords=(
            "ace",
            "boss",
            "clutch",
            "clutched",
            "fail",
            "failed",
            "gg",
            "headshot",
            "insane",
            "kill",
            "killed",
            "kills",
            "loss",
            "lost",
            "no way",
            "reaction",
            "won",
            "win",
        ),
        category="gaming",
    ),
    ContentProfile(
        key="podcast",
        label="Podcast",
        description="Strong opinions, arguments, stories, jokes, quotes and surprises.",
        guidance=(
            "Prioritize strong opinions, disagreements and arguments, complete "
            "stories, jokes and funny exchanges, quotable lines, and surprising or "
            "counterintuitive statements. Avoid exposition and housekeeping talk."
        ),
        keywords=(
            "actually",
            "agree",
            "argument",
            "believe",
            "disagree",
            "funny",
            "joke",
            "never",
            "opinion",
            "quote",
            "shocking",
            "story",
            "surprising",
            "think",
            "truth",
        ),
        category="podcast",
    ),
    ContentProfile(
        key="commentary",
        label="Commentary",
        description="Claims, reactions, controversial moments and emotional peaks.",
        guidance=(
            "Prioritize clear claims and takes, live reactions, controversial or "
            "spicy moments, and emotional peaks. Favor moments where the speaker "
            "commits to a strong point of view."
        ),
        keywords=(
            "actually",
            "believe",
            "best",
            "claim",
            "controversial",
            "crazy",
            "emotional",
            "insane",
            "peak",
            "reaction",
            "unbelievable",
            "worst",
            "wrong",
        ),
        category="commentary",
    ),
)

CONTENT_PROFILES: dict[str, ContentProfile] = {profile.key: profile for profile in _PROFILES}


def list_content_profiles() -> list[ContentProfile]:
    """Return content profiles in display order."""
    return list(_PROFILES)


def get_content_profile(key: str) -> ContentProfile:
    """Return the profile for ``key`` or raise :class:`UnknownContentProfileError`."""
    try:
        return CONTENT_PROFILES[key]
    except KeyError as exc:
        supported = ", ".join(CONTENT_PROFILES)
        raise UnknownContentProfileError(
            f"Unknown content profile '{key}'. Supported profiles: {supported}."
        ) from exc
