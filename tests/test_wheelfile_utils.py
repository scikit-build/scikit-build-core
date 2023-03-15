import stat
import zipfile

from packaging.tags import Tag
from pyproject_metadata import StandardMetadata

import scikit_build_core.build._wheelfile


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
        }
    )
    out_dir = tmp_path / "out"

    wheel = scikit_build_core.build._wheelfile.WheelWriter(
        metadata, out_dir, {Tag("py3", "none", "any")}
    )
    wheel.wheel_metadata.generator = "scikit-build-core 1.2.3"

    monkeypatch.setenv("SOURCE_DATE_EPOCH", "315532800")
    assert wheel.timestamp() == (1980, 1, 1, 0, 0, 0)

    assert wheel.name_ver == "something-1.2.3"
    assert wheel.wheelpath.name == "something-1.2.3-py3-none-any.whl"
    assert wheel.basename == "something-1.2.3-py3-none-any"

    dist_info = wheel.dist_info_contents()
    assert dist_info == {
        "METADATA": b"Metadata-Version: 2.1\nName: something\nVersion: 1.2.3\n",
        "WHEEL": b"Wheel-Version: 1.0\nGenerator: scikit-build-core 1.2.3\nRoot-Is-Purelib: false\nTag: py3-none-any\n\n",
        "entry_points.txt": b"",
    }

    platlib = tmp_path / "platlib"

    with wheel:
        wheel.build({"platlib": platlib})

    assert (out_dir / "something-1.2.3-py3-none-any.whl").exists()

    with zipfile.ZipFile(out_dir / "something-1.2.3-py3-none-any.whl") as zf:
        assert zf.namelist() == [
            "something-1.2.3.dist-info/METADATA",
            "something-1.2.3.dist-info/WHEEL",
            "something-1.2.3.dist-info/entry_points.txt",
            "something-1.2.3.dist-info/RECORD",
        ]

        assert zf.read("something-1.2.3.dist-info/METADATA") == dist_info["METADATA"]
        assert zf.read("something-1.2.3.dist-info/WHEEL") == dist_info["WHEEL"]
        assert (
            zf.read("something-1.2.3.dist-info/entry_points.txt")
            == dist_info["entry_points.txt"]
        )

        for info in zf.infolist():
            assert info.external_attr == (0o664 | stat.S_IFREG) << 16
            assert info.compress_type == zipfile.ZIP_DEFLATED
