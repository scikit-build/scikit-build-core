"""
Compute PEP 794 ``import-names`` / ``import-namespaces`` from the files in a wheel.
"""

from __future__ import annotations

__lazy_modules__ = {
    "keyword",
    "pathlib",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._vendor.pyproject_metadata.constants",
}

import keyword
from pathlib import Path, PurePosixPath

from .._vendor.pyproject_metadata.constants import PRE_2_5_METADATA_VERSIONS

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .._vendor.pyproject_metadata import StandardMetadata

__all__ = ["find_import_names", "package_files", "set_dynamic_import_names"]

IMPORT_FIELDS = ("import-names", "import-namespaces")

_SOURCE_SUFFIXES = (".py",)
_EXTENSION_SUFFIXES = (".so", ".pyd")


def __dir__() -> list[str]:
    return __all__


def _module_name(filename: str) -> str | None:
    """Return the import name of a module file, or None if not importable."""
    if filename.endswith(_SOURCE_SUFFIXES):
        name = filename[: -len(".py")]
    elif filename.endswith(_EXTENSION_SUFFIXES):
        # name.so, name.abi3.so, name.cpython-313-darwin.so, name.cp313-win_amd64.pyd
        name = filename.split(".", 1)[0]
    else:
        return None
    return name if _is_identifier(name) else None


def _is_identifier(name: str) -> bool:
    return name.isidentifier() and not keyword.iskeyword(name)


def find_import_names(
    files: Iterable[PurePosixPath],
) -> tuple[list[str], list[str]]:
    """
    Compute the shortest import names and the namespaces above them from a
    set of file paths relative to the wheel root (``site-packages``).

    A directory with an ``__init__`` module is a package. A directory without
    one is a namespace if it has an importable name below it. A module shadows
    a namespace of the same name.
    """
    tree: dict[str, set[PurePosixPath]] = {}
    names: set[str] = set()
    for path in files:
        if len(path.parts) == 1:
            name = _module_name(path.name)
            if name is not None:
                names.add(name)
        elif _is_identifier(path.parts[0]):
            tree.setdefault(path.parts[0], set()).add(PurePosixPath(*path.parts[1:]))

    namespaces: set[str] = set()
    for dirname, children in tree.items():
        if any(
            len(c.parts) == 1 and _module_name(c.name) == "__init__" for c in children
        ):
            names.add(dirname)
            continue
        sub_names, sub_namespaces = find_import_names(children)
        if sub_names:
            names.update(f"{dirname}.{n}" for n in sub_names)
            namespaces.update(f"{dirname}.{n}" for n in sub_namespaces)
            namespaces.add(dirname)

    namespaces -= names
    return sorted(names), sorted(namespaces)


def package_files(packages: Mapping[str, str]) -> set[PurePosixPath]:
    """
    Collect the files of the wheel packages (destination -> source dir),
    relative to the wheel root.
    """
    return {
        PurePosixPath(dest) / PurePosixPath(f.relative_to(src).as_posix())
        for dest, src in packages.items()
        for f in Path(src).rglob("*")
        if f.is_file()
    }


def set_dynamic_import_names(
    metadata: StandardMetadata, packages: Mapping[str, str]
) -> None:
    """
    Fill the import fields that are still listed in ``project.dynamic`` from
    the wheel packages. Static values (PEP 808) are kept and extended.
    """
    fields = [f for f in IMPORT_FIELDS if f in metadata.dynamic]
    if not fields:
        return

    names, namespaces = find_import_names(package_files(packages))
    static_names = set(metadata.import_names or [])
    static_namespaces = set(metadata.import_namespaces or [])
    # Compare without a "; private" suffix, so static entries win
    static_bare = {n.split(";")[0].strip() for n in static_names | static_namespaces}

    new_names = [n for n in names if n not in static_bare]
    new_namespaces = [n for n in namespaces if n not in static_bare]

    if "import-names" in fields:
        metadata.import_names = [*(metadata.import_names or []), *new_names]
    if "import-namespaces" in fields:
        metadata.import_namespaces = [
            *(metadata.import_namespaces or []),
            *new_namespaces,
        ]
    elif new_namespaces:
        # PEP 794: the parents of a dotted name must be listed too
        msg = (
            f"Found namespace(s) {', '.join(new_namespaces)}; add "
            "'import-namespaces' to project.dynamic or list them in "
            "project.import-namespaces"
        )
        raise ValueError(msg)

    if metadata.metadata_version in PRE_2_5_METADATA_VERSIONS:
        metadata.metadata_version = "2.5"
