from __future__ import annotations

import base64
import copy
import csv
import dataclasses
import hashlib
import io
import os
import stat
import time
import zipfile
from collections.abc import Mapping, Set
from email.message import Message
from email.policy import EmailPolicy
from pathlib import Path
from zipfile import ZipInfo

import packaging.utils
from packaging.tags import Tag
from packaging.utils import BuildTag
from pyproject_metadata import StandardMetadata

from .. import __version__
from .._compat.typing import Self

EMAIL_POLICY = EmailPolicy(max_line_length=0, mangle_from_=False, utf8=True)

MIN_TIMESTAMP = 315532800  # 1980-01-01 00:00:00 UTC


def _b64encode(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


__all__ = ["WheelWriter", "WheelMetadata"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class WheelMetadata:
    root_is_purelib: bool = False
    metadata_version: str = "1.0"
    generator: str = f"scikit-build-core {__version__}"
    build_tag: BuildTag = ()
    tags: Set[Tag] = dataclasses.field(default_factory=frozenset)

    def as_bytes(self) -> bytes:
        msg = Message(policy=EMAIL_POLICY)

        msg["Wheel-Version"] = self.metadata_version
        msg["Generator"] = self.generator
        msg["Root-Is-Purelib"] = str(self.root_is_purelib).lower()
        if self.build_tag:
            msg["Build"] = str(self.build_tag[0]) + self.build_tag[1]

        for tag in sorted(self.tags, key=lambda t: (t.interpreter, t.abi, t.platform)):
            msg["Tag"] = f"{tag.interpreter}-{tag.abi}-{tag.platform}"

        return msg.as_bytes()


@dataclasses.dataclass
class WheelWriter:
    """A general tool for writing wheels. Designed to look a little like ZipFile."""

    metadata: StandardMetadata
    folder: Path
    tags: Set[Tag]
    wheel_metadata = WheelMetadata(root_is_purelib=False)
    buildver: str = ""
    license_files: Mapping[Path, bytes] = dataclasses.field(default_factory=dict)
    _zipfile: zipfile.ZipFile | None = None

    @property
    def name_ver(self) -> str:
        name = packaging.utils.canonicalize_name(self.metadata.name).replace("-", "_")
        # replace - with _ as a local version separator
        version = str(self.metadata.version).replace("-", "_")
        return f"{name}-{version}"

    @property
    def basename(self) -> str:
        pyver = ".".join(sorted({t.interpreter for t in self.tags}))
        abi = ".".join(sorted({t.abi for t in self.tags}))
        arch = ".".join(sorted({t.platform for t in self.tags}))
        optbuildver = [self.buildver] if self.buildver else []
        return "-".join([self.name_ver, *optbuildver, pyver, abi, arch])

    @property
    def wheelpath(self) -> Path:
        return self.folder / f"{self.basename}.whl"

    @property
    def dist_info(self) -> str:
        return f"{self.name_ver}.dist-info"

    @staticmethod
    def timestamp(mtime: float | None = None) -> tuple[int, int, int, int, int, int]:
        timestamp = int(os.environ.get("SOURCE_DATE_EPOCH", mtime or time.time()))
        # The ZIP file format does not support timestamps before 1980.
        timestamp = max(timestamp, MIN_TIMESTAMP)
        return time.gmtime(timestamp)[0:6]

    def dist_info_contents(self) -> dict[str, bytes]:
        entry_points = io.StringIO()
        ep = self.metadata.entrypoints.copy()
        ep["console_scripts"] = self.metadata.scripts
        ep["gui_scripts"] = self.metadata.gui_scripts
        for group, entries in ep.items():
            if entries:
                entry_points.write(f"[{group}]\n")
                for name, target in entries.items():
                    entry_points.write(f"{name} = {target}\n")
                entry_points.write("\n")

        self.wheel_metadata.tags = self.tags

        # Using deepcopy here because of a bug in pyproject-metadata
        # https://github.com/FFY00/python-pyproject-metadata/pull/49
        rfc822 = copy.deepcopy(self.metadata).as_rfc822()
        for fp in self.license_files:
            rfc822["License-File"] = f"{fp}"

        license_entries = {
            f"licenses/{fp}": data for fp, data in self.license_files.items()
        }

        return {
            "METADATA": bytes(rfc822),
            "WHEEL": self.wheel_metadata.as_bytes(),
            "entry_points.txt": entry_points.getvalue().encode("utf-8"),
            **license_entries,
        }

    def build(self, wheel_dirs: dict[str, Path]) -> None:
        assert "platlib" in wheel_dirs
        assert "purelib" not in wheel_dirs
        assert {"platlib", "data", "headers", "scripts", "null"} >= wheel_dirs.keys()

        # The "main" directory (platlib for us) will be handled specially below
        plans = {"": wheel_dirs["platlib"]}
        data_dir = f"{self.name_ver}.data"

        for key in sorted({"data", "headers", "scripts"} & wheel_dirs.keys()):
            plans[key] = wheel_dirs[key]

        for key, path in plans.items():
            for filename in sorted(path.glob("**/*")):
                is_in_dist_info = any(x.endswith(".dist-info") for x in filename.parts)
                is_python_cache = filename.suffix in {".pyc", ".pyo"}
                if filename.is_file() and not is_in_dist_info and not is_python_cache:
                    relpath = filename.relative_to(path)
                    target = Path(data_dir) / key / relpath if key else relpath
                    self.write(str(filename), str(target))

        dist_info_contents = self.dist_info_contents()
        for key, data in dist_info_contents.items():
            self.writestr(f"{self.dist_info}/{key}", data)

    def write(self, filename: str, arcname: str | None = None) -> None:
        """Write a file to the archive. Paths are normalized to Posix paths."""

        with Path(filename).open("rb") as f:
            st = os.fstat(f.fileno())
            data = f.read()

        # Zipfiles require Posix paths for the arcname
        zinfo = ZipInfo(
            (arcname or filename).replace("\\", "/"),
            date_time=self.timestamp(st.st_mtime),
        )
        zinfo.compress_type = zipfile.ZIP_DEFLATED
        zinfo.external_attr = (stat.S_IMODE(st.st_mode) | stat.S_IFMT(st.st_mode)) << 16
        self.writestr(zinfo, data)

    def writestr(self, zinfo_or_arcname: str | ZipInfo, data: bytes) -> None:
        """Write bytes (not strings) to the archive."""
        assert isinstance(data, bytes)
        assert self._zipfile is not None
        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            zinfo = zinfo_or_arcname
        else:
            zinfo = zipfile.ZipInfo(
                zinfo_or_arcname.replace("\\", "/"),
                date_time=self.timestamp(),
            )
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zinfo.external_attr = (0o664 | stat.S_IFREG) << 16
        assert (
            "\\" not in zinfo.filename
        ), f"\\ not supported in zip; got {zinfo.filename!r}"
        self._zipfile.writestr(zinfo, data)

    def __enter__(self) -> Self:
        if not self.wheelpath.parent.exists():
            self.wheelpath.parent.mkdir(parents=True)

        self._zipfile = zipfile.ZipFile(
            self.wheelpath, "w", compression=zipfile.ZIP_DEFLATED
        )
        return self

    def __exit__(self, *args: object) -> None:
        assert self._zipfile is not None
        record = f"{self.dist_info}/RECORD"
        data = io.StringIO()
        writer = csv.writer(data, delimiter=",", quotechar='"', lineterminator="\n")
        for member in self._zipfile.infolist():
            assert (
                "\\" not in member.filename
            ), f"Invalid zip contents: {member.filename}"
            with self._zipfile.open(member) as f:
                member_data = f.read()
            sha = _b64encode(hashlib.sha256(member_data).digest()).decode("ascii")
            writer.writerow((member.filename, f"sha256={sha}", member.file_size))
        writer.writerow((record, "", ""))
        self.writestr(record, data.getvalue().encode("utf-8"))
        self._zipfile.close()
        self._zipfile = None
