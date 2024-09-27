# pylint: disable=duplicate-code
from __future__ import annotations

import contextlib
import copy
import gzip
import io
import os
import tarfile
from pathlib import Path

from packaging.utils import canonicalize_name
from packaging.version import Version

from .. import __version__
from .._compat import tomllib
from .._logging import rich_print
from ..settings.skbuild_read_settings import SettingsReader
from ._file_processor import each_unignored_file
from ._init import setup_logging
from .generate import generate_file_contents
from .metadata import get_standard_metadata
from .wheel import _build_wheel_impl

__all__ = ["build_sdist"]


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

    metadata = get_standard_metadata(pyproject, settings)
    # Using deepcopy here because of a bug in pyproject-metadata
    # https://github.com/FFY00/python-pyproject-metadata/pull/49
    pkg_info = bytes(copy.deepcopy(metadata).as_rfc822())

    # Only normalize SDist name if 0.5+ is requested for backwards compat
    should_normalize_name = (
        settings.minimum_version is None or settings.minimum_version >= Version("0.5")
    )

    sdist_name = (
        canonicalize_name(metadata.name).replace("-", "_")
        if should_normalize_name
        else metadata.name
    )
    srcdirname = f"{sdist_name}-{metadata.version}"
    filename = f"{srcdirname}.tar.gz"

    if settings.sdist.cmake:
        _build_wheel_impl(
            None, config_settings, None, exit_after_config=True, editable=False
        )

    for gen in settings.generate:
        if gen.location == "source":
            contents = generate_file_contents(gen, metadata)
            gen.path.write_text(contents)
            settings.sdist.include.append(str(gen.path))

    sdist_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        gzip_container = stack.enter_context(
            gzip.GzipFile(
                sdist_dir / filename, mode="wb", compresslevel=9, mtime=timestamp
            )
        )
        tar = stack.enter_context(
            tarfile.TarFile(fileobj=gzip_container, mode="w", format=tarfile.PAX_FORMAT)
        )
        paths = sorted(
            each_unignored_file(
                Path(),
                include=settings.sdist.include,
                exclude=settings.sdist.exclude,
                build_dir=settings.build_dir,
            )
        )
        for filepath in paths:
            tar.add(
                filepath,
                arcname=srcdirname / filepath,
                filter=normalize_tar_info if reproducible else lambda x: x,
            )

        add_bytes_to_tar(
            tar, pkg_info, f"{srcdirname}/PKG-INFO", normalize=reproducible
        )

    return filename
