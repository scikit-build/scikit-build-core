import stat
import sys
import time
import zipfile
from pathlib import Path

import pytest
from packaging.tags import Tag

import scikit_build_core.build._wheelfile
from scikit_build_core._reproducible import get_reproducible_epoch
from scikit_build_core._vendor.pyproject_metadata import StandardMetadata
from scikit_build_core.build._wheelfile import WheelWriter


def _make_writer(tmp_path: Path, *, reproducible: bool = True) -> WheelWriter:
    metadata = StandardMetadata.from_pyproject(
        {"project": {"name": "something", "version": "1.2.3"}},
        metadata_version="2.3",
    )
    return scikit_build_core.build._wheelfile.WheelWriter(
        metadata,
        tmp_path / "out",
        {Tag("py3", "none", "any")},
        scikit_build_core.build._wheelfile.WheelMetadata(),
        None,
        reproducible=reproducible,
    )


def test_wheel_timestamp_reproducible_fixed_epoch(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    wheel = _make_writer(tmp_path)
    expected = time.gmtime(get_reproducible_epoch())[0:6]
    # A per-file mtime is ignored in reproducible mode.
    assert wheel.timestamp(0) == expected
    assert wheel.timestamp() == expected


def test_wheel_timestamp_non_reproducible_uses_mtime(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    wheel = _make_writer(tmp_path, reproducible=False)
    mtime = 1234567890
    assert wheel.timestamp(mtime) == time.gmtime(mtime)[0:6]


def test_wheel_write_normalizes_permissions(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    src = tmp_path / "src.txt"
    src.write_text("data")
    src.chmod(0o600)

    wheel = _make_writer(tmp_path)
    with wheel:
        wheel.write(str(src), "src.txt")
    with zipfile.ZipFile(wheel.wheelpath) as zf:
        info = zf.getinfo("src.txt")
        # A non-executable file normalizes to 0o644 on every platform.
        assert stat.S_IMODE(info.external_attr >> 16) == 0o644


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX permissions")
def test_wheel_write_permissions_posix(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    src = tmp_path / "exe"
    src.write_text("data")
    src.chmod(0o777)

    out_dir = tmp_path / "out"
    # Reproducible mode normalizes an executable to 0o755; otherwise the raw mode
    # is preserved.
    for reproducible, expected in [(True, 0o755), (False, 0o777)]:
        wheel = _make_writer(tmp_path, reproducible=reproducible)
        wheel.folder = out_dir / str(reproducible)
        with wheel:
            wheel.write(str(src), "exe")
        with zipfile.ZipFile(wheel.wheelpath) as zf:
            info = zf.getinfo("exe")
            assert stat.S_IMODE(info.external_attr >> 16) == expected


def test_wheel_reproducible_normalizes_generated_metadata(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    wheel = _make_writer(tmp_path)
    platlib = tmp_path / "platlib"
    platlib.mkdir()
    with wheel:
        wheel.build({"platlib": platlib})
    with zipfile.ZipFile(wheel.wheelpath) as zf:
        # Generated .dist-info entries are written via writestr, not write; they
        # must be normalized too in reproducible mode.
        for info in zf.infolist():
            assert stat.S_IMODE(info.external_attr >> 16) == 0o644


def test_wheel_metadata() -> None:
    metadata = scikit_build_core.build._wheelfile.WheelMetadata(
        generator="scikit-build-core 1.2.3"
    )
    assert (
        metadata.as_bytes()
        == b"Wheel-Version: 1.0\nGenerator: scikit-build-core 1.2.3\nRoot-Is-Purelib: false\n\n"
    )


def test_wheel_writer_simple(tmp_path, monkeypatch):
    metadata = StandardMetadata.from_pyproject(
        {
            "project": {
                "name": "something",
                "version": "1.2.3",
            },
        },
        metadata_version="2.3",
    )
    out_dir = tmp_path / "out"

    wheel = scikit_build_core.build._wheelfile.WheelWriter(
        metadata,
        out_dir,
        {Tag("py3", "none", "any")},
        scikit_build_core.build._wheelfile.WheelMetadata(),
        None,
    )
    wheel.wheel_metadata.generator = "scikit-build-core 1.2.3"

    monkeypatch.setenv("SOURCE_DATE_EPOCH", "315532800")
    assert wheel.timestamp() == (1980, 1, 1, 0, 0, 0)

    assert wheel.name_ver == "something-1.2.3"
    assert wheel.wheelpath.name == "something-1.2.3-py3-none-any.whl"
    assert wheel.basename == "something-1.2.3-py3-none-any"

    dist_info = wheel.dist_info_contents()
    assert dist_info == {
        "METADATA": b"Metadata-Version: 2.3\nName: something\nVersion: 1.2.3\n\n",
        "WHEEL": b"Wheel-Version: 1.0\nGenerator: scikit-build-core 1.2.3\nRoot-Is-Purelib: false\nTag: py3-none-any\n\n",
    }

    platlib = tmp_path / "platlib"

    with wheel:
        wheel.build({"platlib": platlib})

    assert (out_dir / "something-1.2.3-py3-none-any.whl").exists()

    with zipfile.ZipFile(out_dir / "something-1.2.3-py3-none-any.whl") as zf:
        assert zf.namelist() == [
            "something-1.2.3.dist-info/METADATA",
            "something-1.2.3.dist-info/WHEEL",
            "something-1.2.3.dist-info/RECORD",
        ]

        assert zf.read("something-1.2.3.dist-info/METADATA") == dist_info["METADATA"]
        assert zf.read("something-1.2.3.dist-info/WHEEL") == dist_info["WHEEL"]

        for info in zf.infolist():
            assert info.external_attr == (0o664 | stat.S_IFREG) << 16
            assert info.compress_type == zipfile.ZIP_DEFLATED


def test_wheel_writer_variant(tmp_path):
    metadata = StandardMetadata.from_pyproject(
        {
            "project": {
                "name": "something",
                "version": "1.2.3",
            },
        },
        metadata_version="2.3",
    )
    out_dir = tmp_path / "out"

    wheel = scikit_build_core.build._wheelfile.WheelWriter(
        metadata,
        out_dir,
        {Tag("py3", "none", "any")},
        scikit_build_core.build._wheelfile.WheelMetadata(),
        None,
        variant_label="cpu",
        variant_dist_info_contents=b'{"variant":"cpu"}',
    )

    assert wheel.wheelpath.name == "something-1.2.3-py3-none-any-cpu.whl"
    assert wheel.dist_info_contents()["variant.json"] == b'{"variant":"cpu"}'


def test_wheel_writer_variant_metadata_dir_conflict(tmp_path):
    metadata = StandardMetadata.from_pyproject(
        {
            "project": {
                "name": "something",
                "version": "1.2.3",
            },
        },
        metadata_version="2.3",
    )
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    (metadata_dir / "variant.json").write_bytes(b'{"variant":"override"}')

    wheel = scikit_build_core.build._wheelfile.WheelWriter(
        metadata,
        tmp_path / "out",
        {Tag("py3", "none", "any")},
        scikit_build_core.build._wheelfile.WheelMetadata(),
        metadata_dir,
        variant_label="cpu",
        variant_dist_info_contents=b'{"variant":"cpu"}',
    )

    with pytest.raises(ValueError, match=r"variant\.json"):
        wheel.dist_info_contents()
