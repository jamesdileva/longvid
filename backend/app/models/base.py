"""Shared helpers for ORM model definitions."""

from __future__ import annotations

import enum


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """values_callable for SQLAlchemy Enum columns.

    Stores member *values* (e.g. ``active``) instead of names (``ACTIVE``),
    keeping the database representation aligned with API/JSON values.
    """
    return [member.value for member in enum_cls]
