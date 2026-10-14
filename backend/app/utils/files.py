"""Filesystem helpers: safe names and path containment."""

from __future__ import annotations

import re
from pathlib import Path

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_NAME_LENGTH = 120


def safe_filename(name: str, fallback: str = "file") -> str:
    """Reduce an arbitrary filename to a conservative, portable form.

    Strips directory components, unsafe characters, and length while keeping
    the extension. Used before writing anything derived from user input.
    """
    base = Path(name).name  # no directory traversal via input
    base = _UNSAFE_CHARS.sub("_", base).strip("._") or fallback
    if len(base) > _MAX_NAME_LENGTH:
        suffix = Path(base).suffix
        stem = Path(base).stem
        base = stem[: _MAX_NAME_LENGTH - len(suffix)] + suffix
    return base


def unique_filename(filename: str, token_length: int = 12) -> str:
    """Prefix a filename with random hex so imports never collide."""
    import secrets

    return f"{secrets.token_hex(token_length // 2)}_{safe_filename(filename)}"


def is_within(child: Path, parent: Path) -> bool:
    """True when ``child`` resolves inside ``parent``."""
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True
