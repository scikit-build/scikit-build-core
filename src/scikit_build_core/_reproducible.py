from __future__ import annotations

import os

__all__ = ["MIN_TIMESTAMP", "get_reproducible_epoch", "normalize_file_permissions"]

# The ZIP file format does not support timestamps before 1980-01-01 00:00:00 UTC.
MIN_TIMESTAMP = 315532800


def __dir__() -> list[str]:
    return __all__


def get_reproducible_epoch() -> int:
    """
    Return an integer representing the integer number of seconds since the Unix epoch.

    If the `SOURCE_DATE_EPOCH` environment variable is set, use that value. Otherwise,
    always return `1667997441`.
    """
    return int(os.environ.get("SOURCE_DATE_EPOCH", "1667997441"))


def normalize_file_permissions(st_mode: int) -> int:
    """
    Normalize the permission bits in the st_mode field from stat to 644/755
    Popular VCSs only track whether a file is executable or not. The exact
    permissions can vary on systems with different umasks. Normalising
    to 644 (non executable) or 755 (executable) makes builds more reproducible.

    Taken from https://github.com/pypa/flit/blob/6a2a8c6462e49f584941c667b70a6f48a7b3f9ab/flit_core/flit_core/common.py#L257
    """
    # Set 644 permissions, leaving higher bits of st_mode unchanged
    new_mode = (st_mode | 0o644) & ~0o133
    if st_mode & 0o100:
        new_mode |= 0o111  # Executable: 644 -> 755
    return new_mode
