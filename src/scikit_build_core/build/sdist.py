# pylint: disable=duplicate-code
from __future__ import annotations

__lazy_modules__ = {
    "contextlib",
    "copy",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._compat",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._logging",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._reproducible",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}.settings",
    f"{__spec__.parent}._file_processor",
    f"{__spec__.parent}._init",
    f"{__spec__.parent}._pathutil",
    f"{__spec__.parent}.generate",
    f"{__spec__.parent}.metadata",
    f"{__spec__.parent}.wheel",
    "gzip",
    "io",
    "packaging",
    "packaging.utils",
    "pathlib",
    "pathspec",
    "tarfile",
}

import contextlib
import copy
import gzip
import io
import tarfile
from pathlib import Path

import pathspec
from packaging.utils import canonicalize_name

from .. import __version__
from .._compat import tomllib
from .._logging import rich_print, rich_warning
from .._reproducible import get_reproducible_epoch, normalize_file_permissions
from ..settings.skbuild_read_settings import SettingsReader
from ._file_processor import each_unignored_file
from ._init import setup_logging
from ._pathutil import iter_force_include
from .generate import generate_file_contents
from .metadata import get_standard_metadata
from .wheel import _build_wheel_impl

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["build_sdist"]


def __dir__() -> list[str]:
    return __all__


def normalize_tar_info(tar_info: tarfile.TarInfo) -> tarfile.TarInfo:
    """
    Normalize the TarInfo associated with a file to improve reproducibility.

    Inspired by Hatch
    https://github.com/pypa/hatch/blob/573192f88022bb781c698dae2c0b84ef3fb9a7ad/backend/src/hatchling/builders/sdist.py#L51
    """
    tar_info = copy.copy(tar_info)
    tar_info.uname = ""
    tar_info.gname = ""
    tar_info.uid = 0
    tar_info.gid = 0
    tar_info.mode = normalize_file_permissions(tar_info.mode)
    tar_info.mtime = get_reproducible_epoch()
    return tar_info


def add_bytes_to_tar(
    tar: tarfile.TarFile, data: bytes, name: str, *, normalize: bool
) -> None:
    """
    Write ``data`` bytes to ``name`` in a tarfile ``tar``. Normalize the info if
    ``normalize`` is true.
    """

    tarinfo = tarfile.TarInfo(name)
    if normalize:
        tarinfo = normalize_tar_info(tarinfo)
    with io.BytesIO(data) as bio:
        tarinfo.size = bio.getbuffer().nbytes
        tar.addfile(tarinfo, bio)


def add_path_to_tar(
    tar: tarfile.TarFile,
    filepath: Path,
    arcname: Path,
    *,
    tar_filter: Callable[[tarfile.TarInfo], tarfile.TarInfo],
) -> None:
    """
    Add ``filepath`` to ``tar`` at ``arcname``, applying ``tar_filter`` for
    reproducibility normalization.

    ``tar.dereference`` (``sdist.resolve-symlinks = "all"``) makes ``tar.add``
    stat through symlinks; a dangling symlink then raises ``FileNotFoundError``
    instead of being archived (#1417). Fall back to storing the symlink itself
    in that case, matching the pre-1.0 behavior, and warn.
    """
    if tar.dereference and filepath.is_symlink() and not filepath.exists():
        rich_warning(
            f"{filepath} is a dangling symlink; storing it as a symlink instead "
            'of resolving it. Set sdist.resolve-symlinks = "none" to silence '
            "this warning."
        )
        tar.dereference = False
        try:
            tar.add(filepath, arcname=arcname, filter=tar_filter)
        finally:
            tar.dereference = True
    else:
        tar.add(filepath, arcname=arcname, filter=tar_filter)


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, list[str] | str] | None = None,
) -> str:
    rich_print(
        f"{{green}}***{{bold.green}} scikit-build-core {__version__}{{red}} (sdist)",
    )

    with Path("pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)

    settings_reader = SettingsReader(pyproject, config_settings or {}, state="sdist")
    settings = settings_reader.settings
    setup_logging(settings.logging.level)

    settings_reader.validate_may_exit()

    sdist_dir = Path(sdist_directory)

    reproducible = settings.sdist.reproducible
    timestamp = get_reproducible_epoch() if reproducible else None

    metadata = get_standard_metadata(pyproject, settings, build_state="sdist")
    pkg_info = bytes(metadata.as_rfc822())

    # Names must be normalized per PEP 625
    sdist_name = canonicalize_name(metadata.name).replace("-", "_")
    srcdirname = f"{sdist_name}-{metadata.version}"
    filename = f"{srcdirname}.tar.gz"

    if settings.sdist.cmake:
        _build_wheel_impl(
            None, config_settings, None, exit_after_config=True, editable=False
        )

    for gen in settings.generate:
        if gen.location == "source":
            contents = generate_file_contents(gen, metadata)
            gen.path.write_text(contents, encoding="utf-8")
            settings.sdist.include.append(gen.path.as_posix())

    sdist_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        gzip_container = stack.enter_context(
            gzip.GzipFile(
                sdist_dir / filename, mode="wb", compresslevel=9, mtime=timestamp
            )
        )
        tar = stack.enter_context(
            tarfile.TarFile(
                fileobj=gzip_container,
                mode="w",
                format=tarfile.PAX_FORMAT,
                dereference=settings.sdist.resolve_symlinks == "all",
            )
        )
        assert settings.sdist.inclusion_mode is not None
        paths = sorted(
            each_unignored_file(
                Path(),
                include=settings.sdist.include,
                exclude=settings.sdist.exclude,
                build_dir=settings.build_dir,
                mode=settings.sdist.inclusion_mode,
            )
        )
        for filepath in paths:
            add_path_to_tar(
                tar,
                filepath,
                arcname=srcdirname / filepath,
                tar_filter=normalize_tar_info if reproducible else lambda x: x,
            )

        # A force-included file is forced in; a force-included directory's
        # members stay subject to sdist.exclude (mirrors wheel.force-include).
        sdist_exclude_spec = pathspec.GitIgnoreSpec.from_lines(settings.sdist.exclude)
        forced = []
        for source, dest in settings.sdist.force_include.items():
            source_is_file = Path(source).expanduser().is_file()
            for src_file, target in iter_force_include(source, dest, Path(srcdirname)):
                if not source_is_file and sdist_exclude_spec.match_file(
                    target.relative_to(srcdirname)
                ):
                    continue
                forced.append((src_file, target))
        # Sort by archive name so the tar member order (and thus the reproducible
        # .tar.gz bytes) does not depend on filesystem ordering for directories.
        forced.sort(key=lambda pair: pair[1])
        for src_file, target in forced:
            add_path_to_tar(
                tar,
                src_file,
                arcname=target,
                tar_filter=normalize_tar_info if reproducible else lambda x: x,
            )

        add_bytes_to_tar(
            tar, pkg_info, f"{srcdirname}/PKG-INFO", normalize=reproducible
        )

    return filename
