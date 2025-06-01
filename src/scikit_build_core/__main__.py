from __future__ import annotations

from ._logging import rich_print

__all__ = ["main"]


def __dir__() -> list[str]:
    return __all__


def main() -> None:
    rich_print("{blue}A top level CLI is not currently provided for scikit-build-core.")
    rich_print("{blue}However, the following modules have CLI utilities:")
    rich_print(
        "  python -m scikit_build_core.build requires       {green}Get the build requirements"
    )
    rich_print(
        "  python -m scikit_build_core.build project-table  {green}Get the project table (with dynamic metadata)"
    )
    rich_print(
        "  python -m scikit_build_core.builder              {green}Info about the system"
    )
    rich_print(
        "  python -m scikit_build_core.builder.wheel_tag    {green}Info about the computed wheel tag"
    )
    rich_print(
        "  python -m scikit_build_core.builder.sysconfig    {green}Info from sysconfig"
    )
    rich_print(
        "  python -m scikit_build_core.file_api.query       {green}Request CMake file API"
    )
    rich_print(
        "  python -m scikit_build_core.file_api.reply       {green}Process CMake file API"
    )
    rich_print()


if __name__ == "__main__":
    main()
