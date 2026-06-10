"""Helper dataclasses for JSON-schema tests.

Deliberately *without* ``from __future__ import annotations`` so that field
annotations resolve to real types (matching the settings model modules).
"""

import dataclasses


@dataclasses.dataclass
class HasUnderscoreRequired:
    """A dataclass with an underscore-named required field."""

    required_field: str
