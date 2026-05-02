from __future__ import annotations

import tarfile
import textwrap
import typing
import zipfile

import pytest

from scikit_build_core.build import build_sdist, build_wheel
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

if typing.TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("package", ["simple_purelib_package"], indirect=True)
def test_force_include_sdist_and_wheel(package, tmp_path: Path):
    extra_dir = tmp_path / "external"
    external_file = extra_dir / "nested" / "data.txt"
    external_file.parent.mkdir(parents=True)
    external_file.write_text("hello", encoding="utf-8")

    pyproject_path = package.workdir / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8")
        + textwrap.dedent(
            f"""

            [[tool.scikit-build.force-include]]
            source = {str(extra_dir)!r}
            sdist = "src/vendor_data"
            wheel = "purelib_example/vendor_data"
            """
        ),
        encoding="utf-8",
    )

    dist = tmp_path / "dist"
    sdist_name = build_sdist(str(dist))
    sdist = dist / sdist_name

    with tarfile.open(sdist) as tf:
        names = set(tf.getnames())

    assert "purelib_example-0.0.1/src/vendor_data/nested/data.txt" in names

    wheel_name = build_wheel(str(dist), {})
    wheel = dist / wheel_name

    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())

    assert "purelib_example/vendor_data/nested/data.txt" in names


def test_force_include_requires_target(tmp_path: Path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        textwrap.dedent(
            """
            [tool.scikit-build]
            [[tool.scikit-build.force-include]]
            source = "../vendor_data"
            """
        ),
        encoding="utf-8",
    )

    settings_reader = SettingsReader.from_file(pyproject_toml, {})

    with pytest.raises(SystemExit):
        settings_reader.validate_may_exit()
