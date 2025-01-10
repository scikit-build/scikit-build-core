from __future__ import annotations

import base64
import csv
import dataclasses
import hashlib
import io
import os
import stat
import time
import zipfile
from email.message import Message
from email.policy import EmailPolicy
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipInfo

import pathspec

from .. import __version__

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence, Set

    from packaging.tags import Tag

    from .._compat.typing import Self
    from .._vendor.pyproject_metadata import StandardMetadata

EMAIL_POLICY = EmailPolicy(max_line_length=0, mangle_from_=False, utf8=True)

MIN_TIMESTAMP = 315532800  # 1980-01-01 00:00:00 UTC


def _b64encode(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


__all__ = ["WheelMetadata", "WheelWriter"]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass
class WheelMetadata:
    root_is_purelib: bool = False
    metadata_version: str = "1.0"
    generator: str = f"scikit-build-core {__version__}"
    tags: Set[Tag] = dataclasses.field(default_factory=frozenset)
    build_tag: str = ""

    def as_bytes(self) -> bytes:
        msg = Message(policy=EMAIL_POLICY)

        msg["Wheel-Version"] = self.metadata_version
        msg["Generator"] = self.generator
        msg["Root-Is-Purelib"] = str(self.root_is_purelib).lower()

        for tag in sorted(self.tags, key=lambda t: (t.interpreter, t.abi, t.platform)):
            msg["Tag"] = f"{tag.interpreter}-{tag.abi}-{tag.platform}"
        if self.build_tag:
            msg["Build"] = self.build_tag

        return msg.as_bytes()


@dataclasses.dataclass
class WheelWriter:
    """A general tool for writing wheels. Designed to look a little like ZipFile."""

    metadata: StandardMetadata
    folder: Path
    tags: Set[Tag]
    wheel_metadata: WheelMetadata
    metadata_dir: Path | None
    _zipfile: zipfile.ZipFile | None = None

    @property
    def name_ver(self) -> str:
        name = self.metadata.canonical_name.replace("-", "_")
        # replace - with _ as a local version separator
        version = str(self.metadata.version).replace("-", "_")
        return f"{name}-{version}"

    @property
    def basename(self) -> str:
        pyver = ".".join(sorted({t.interpreter for t in self.tags}))
        abi = ".".join(sorted({t.abi for t in self.tags}))
        arch = ".".join(sorted({t.platform for t in self.tags}))
        optbuildver = (
            [self.wheel_metadata.build_tag] if self.wheel_metadata.build_tag else []
        )
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

        rfc822 = self.metadata.as_rfc822()

        metadata_files = self.metadata_dir.rglob("*") if self.metadata_dir else []
        extra_metadata = {
            str(f.relative_to(self.metadata_dir or Path())): f.read_bytes()
            for f in metadata_files
            if f.is_file()
        }
        if {"METADATA", "WHEEL", "RECORD", "entry_points.txt"} & extra_metadata.keys():
            msg = "Cannot have METADATA, WHEEL, RECORD, or entry_points.txt in metadata_dir"
            raise ValueError(msg)

        entry_points_txt = entry_points.getvalue().encode("utf-8")
        entry_points_dict = (
            {"entry_points.txt": entry_points_txt} if entry_points_txt else {}
        )

        return {
            "METADATA": bytes(rfc822),
            "WHEEL": self.wheel_metadata.as_bytes(),
            **entry_points_dict,
            **extra_metadata,
        }

    def build(
        self, wheel_dirs: Mapping[str, Path], exclude: Sequence[str] = ()
    ) -> None:
        (targetlib,) = {"platlib", "purelib"} & set(wheel_dirs)
        assert {
            targetlib,
            "data",
            "headers",
            "scripts",
            "null",
            "metadata",
        } >= wheel_dirs.keys()

        # The "main" directory (platlib usually for us) will be handled specially below
        plans = {"": wheel_dirs[targetlib]}
        data_dir = f"{self.name_ver}.data"

        for key in sorted({"data", "headers", "scripts"} & wheel_dirs.keys()):
            plans[key] = wheel_dirs[key]

        exclude_spec = pathspec.GitIgnoreSpec.from_lines(exclude)

        for key, path in plans.items():
            for filename in sorted(path.glob("**/*")):
                if not filename.is_file():
                    continue
                if any(x.endswith(".dist-info") for x in filename.parts):
                    continue
                if filename.suffix in {".pyc", ".pyo"}:
                    continue
                relpath = filename.relative_to(path)
                if exclude_spec.match_file(relpath):
                    continue
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
        assert "\\" not in zinfo.filename, (
            f"\\ not supported in zip; got {zinfo.filename!r}"
        )
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
            assert "\\" not in member.filename, (
                f"Invalid zip contents: {member.filename}"
            )
            with self._zipfile.open(member) as f:
                member_data = f.read()
            sha = _b64encode(hashlib.sha256(member_data).digest()).decode("ascii")
            writer.writerow((member.filename, f"sha256={sha}", member.file_size))
        writer.writerow((record, "", ""))
        self.writestr(record, data.getvalue().encode("utf-8"))
        self._zipfile.close()
        self._zipfile = None
