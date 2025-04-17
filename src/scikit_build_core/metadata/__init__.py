from __future__ import annotations

__all__: list[str] = ["_DICT_LIST_FIELDS", "_LIST_STR_FIELDS", "_STR_FIELDS"]


# Name is not dynamically settable, so not in this list
_STR_FIELDS = frozenset(
    [
        "version",
        "description",
        "requires-python",
        "license",
    ]
)

# Dynamic is not dynamically settable, so not in this list
_LIST_STR_FIELDS = frozenset(
    [
        "classifiers",
        "keywords",
        "dependencies",
        "license_files",
    ]
)

_DICT_LIST_FIELDS = frozenset(
    [
        "urls",
        "optional-dependencies",
    ]
)
