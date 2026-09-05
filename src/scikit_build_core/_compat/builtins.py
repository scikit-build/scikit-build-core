from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup
else:
    from builtins import ExceptionGroup

__all__ = ["ExceptionGroup", "add_note"]


def __dir__() -> list[str]:
    return __all__


def add_note(exc: BaseException, note: str) -> None:
    """
    Attach a note to an exception. ``BaseException.add_note`` is 3.11+, so set
    ``__notes__`` by hand on older Pythons.
    """
    if sys.version_info < (3, 11):
        notes = "__notes__"  # set so linters won't try to be clever
        setattr(exc, notes, [*getattr(exc, notes, []), note])
    else:
        exc.add_note(note)
