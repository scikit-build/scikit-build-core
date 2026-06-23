from __future__ import annotations

import argparse
import string
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.utils import canonicalize_name

from .._logging import rich_error, rich_print
from ..resources import resources

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["main", "populate_parser"]


def __dir__() -> list[str]:
    return __all__


# Order shown in the interactive menu.
BACKENDS = ("pybind11", "nanobind", "c", "cython", "swig", "fortran", "abi3")

# Template files that live in the project root rather than in the package.
_ROOT_FILES = frozenset({"pyproject.toml", "CMakeLists.txt"})

_INIT_PY = 'from ._core import square\n\n__all__ = ["square"]\n'


def _select_backend() -> str:
    """Prompt the user to pick a backend, or error if not interactive."""
    if not sys.stdin.isatty():
        rich_error(
            "No backend selected. Pass {bold}--backend{normal} (one of: {choices}).",
            choices=", ".join(BACKENDS),
        )
    rich_print("{bold}Select a binding backend:{normal}")
    for index, name in enumerate(BACKENDS, start=1):
        rich_print("  {blue}{index}{normal}) {name}", index=index, name=name)
    while True:
        choice = input(f"Enter a number [1-{len(BACKENDS)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(BACKENDS):
            return BACKENDS[int(choice) - 1]
        rich_print("{yellow}Invalid selection, try again.{normal}")


def _generate(
    directory: Path, backend: str, project_name: str, module: str
) -> list[Path]:
    """Write the rendered template for ``backend`` into ``directory``."""
    template_dir = resources / "templates" / backend
    package_dir = directory / "src" / module
    package_dir.mkdir(parents=True, exist_ok=True)

    substitutions = {"project_name": project_name, "module": module}
    written: list[Path] = []
    for entry in sorted(template_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_file():
            continue
        text = string.Template(entry.read_text(encoding="utf-8")).safe_substitute(
            substitutions
        )
        dest = (
            directory / entry.name
            if entry.name in _ROOT_FILES
            else package_dir / entry.name
        )
        dest.write_text(text, encoding="utf-8")
        written.append(dest)

    init_py = package_dir / "__init__.py"
    init_py.write_text(_INIT_PY, encoding="utf-8")
    written.append(init_py)
    return sorted(written)


def _display(path: Path) -> str:
    """Show ``path`` relative to the working directory when possible."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _report(directory: Path, backend: str, module: str, written: list[Path]) -> None:
    rich_print("{bold.green}Created a {backend} project!{normal}", backend=backend)
    for path in written:
        rich_print("  {green}+{normal} {path}", path=_display(path))
    rich_print()
    rich_print("{bold}Next steps:{normal}")
    if directory != Path.cwd():
        rich_print("  {cyan}cd {directory}{normal}", directory=_display(directory))
    rich_print("  {cyan}pip install .{normal}")
    rich_print(
        '  {cyan}python -c "import {module}; print({module}.square(3))"{normal}',
        module=module,
    )


def main_init(args: argparse.Namespace, /) -> None:
    backend: str = args.backend or _select_backend()
    directory: Path = args.directory.resolve()
    raw_name: str = args.name or directory.name
    project_name = canonicalize_name(raw_name)
    if not project_name:
        rich_error(
            "Could not derive a valid project name from {raw_name!r}; pass {bold}--name{normal}.",
            raw_name=raw_name,
        )
    module = project_name.replace("-", "_").replace(".", "_")

    if directory.is_dir() and any(directory.iterdir()) and not args.force:
        rich_error(
            "Directory {directory} is not empty; pass {bold}--force{normal} to generate anyway.",
            directory=directory,
        )

    written = _generate(directory, backend, project_name, module)
    _report(directory, backend, module, written)


def populate_parser(parser: argparse.ArgumentParser, /) -> None:
    """Add the ``init`` arguments to an existing parser."""
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path(),
        help="Directory to create the project in (default: current directory)",
    )
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        help="Binding backend to use (prompts interactively if omitted)",
    )
    parser.add_argument(
        "--name",
        help="Project name (default: derived from the directory name)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Generate into a non-empty directory",
    )
    parser.set_defaults(func=main_init)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scikit_build_core.init",
        allow_abbrev=False,
        description="Generate a minimal CMake + scikit-build-core starter project.",
    )
    populate_parser(parser)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
