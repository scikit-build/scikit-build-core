from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from scikit_build_core._logging import rich_warning
from scikit_build_core.build import build_sdist

PREFIX = "cmake_example-0.0.1"

# Expected tar member type per resolve-symlinks mode: "reg", "sym", or None
# (absent from the archive). A directory symlink loop cannot be resolved, so
# every mode stores it as a symlink member (on any platform).
EXPECTED = {
    "all": {
        "CMakeLists_link.txt": "reg",
        "src_link": None,
        "src_link/main.cpp": "reg",
        "ext_file.txt": "reg",
        "ext_dir": None,
        "ext_dir/data.txt": "reg",
        "src/loop": "sym",
        "src/loop/main.cpp": None,
    },
    "external": {
        "CMakeLists_link.txt": "sym",
        "src_link": "sym",
        "src_link/main.cpp": None,
        "ext_file.txt": "reg",
        "ext_dir": None,
        "ext_dir/data.txt": "reg",
        "src/loop": "sym",
        "src/loop/main.cpp": None,
    },
    "none": {
        "CMakeLists_link.txt": "sym",
        "src_link": "sym",
        "src_link/main.cpp": None,
        "ext_file.txt": "sym",
        "ext_dir": "sym",
        "ext_dir/data.txt": None,
        "src/loop": "sym",
        "src/loop/main.cpp": None,
    },
    "classic": {
        "CMakeLists_link.txt": "sym",
        "src_link": None,
        "src_link/main.cpp": "reg",
        "ext_file.txt": "sym",
        "ext_dir": None,
        "ext_dir/data.txt": "reg",
        "src/loop": "sym",
        "src/loop/main.cpp": None,
    },
}


@pytest.fixture
def can_symlink(tmp_path: Path) -> None:
    """Skip the test if symlinks are not supported on this OS."""
    target = tmp_path / "target"
    target.touch()
    try:
        tmp_path.joinpath("link").symlink_to(target)
    except OSError:
        pytest.skip(
            "Creating symlinks is not supported/allowed on this OS without privileges"
        )


@pytest.mark.usefixtures("package_simple_pyproject_ext", "can_symlink")
@pytest.mark.parametrize("mode", [None, "all", "external", "none", "classic"])
def test_pep517_sdist_symlink(tmp_path: Path, mode: str | None) -> None:
    # Targets outside the project directory.
    outside = tmp_path / "outside"
    outside.mkdir()
    # Bytes, not text: text mode would write \r\n on Windows and break the
    # dereferenced-content check below.
    outside.joinpath("ext.txt").write_bytes(b"external file\n")
    outside.joinpath("extdir").mkdir()
    outside.joinpath("extdir", "data.txt").write_bytes(b"external data\n")

    # Internal file and directory symlinks, external file and directory
    # symlinks, and a directory symlink loop.
    Path("CMakeLists_link.txt").symlink_to("CMakeLists.txt")
    Path("src_link").symlink_to("src", target_is_directory=True)
    Path("ext_file.txt").symlink_to(outside / "ext.txt")
    Path("ext_dir").symlink_to(outside / "extdir", target_is_directory=True)
    Path("src", "loop").symlink_to(Path("..", "src"), target_is_directory=True)

    config_settings: dict[str, list[str] | str] | None = (
        {"sdist.resolve-symlinks": mode} if mode else None
    )
    out = build_sdist(str(tmp_path), config_settings=config_settings)

    with tarfile.open(tmp_path / out, "r:gz") as tar:
        members = {m.name: m for m in tar.getmembers()}
        for name, expected in EXPECTED[mode or "all"].items():
            member = members.get(f"{PREFIX}/{name}")
            if expected is None:
                assert member is None, f"{name} should not be in the SDist"
            elif expected == "reg":
                assert member is not None, f"{name} missing from the SDist"
                assert member.isreg(), f"{name} should be a regular file"
            else:
                assert member is not None, f"{name} missing from the SDist"
                assert member.issym(), f"{name} should be a symlink"

        if mode == "external":
            # The external file symlink is stored dereferenced.
            fobj = tar.extractfile(f"{PREFIX}/ext_file.txt")
            assert fobj is not None
            assert fobj.read() == b"external file\n"
        if mode in {"none", "external"}:
            # Internal symlink targets are preserved as-is.
            link = members[f"{PREFIX}/CMakeLists_link.txt"]
            assert link.linkname == "CMakeLists.txt"
            dir_link = members[f"{PREFIX}/src_link"]
            assert dir_link.linkname == "src"


@pytest.mark.usefixtures("package_simple_pyproject_ext", "can_symlink")
def test_pep517_sdist_dangling_symlink(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    A dangling symlink cannot be dereferenced; with the ``resolve-symlinks =
    "all"`` default the build must fall back to storing it as a symlink member
    instead of crashing (#1417).
    """
    Path("dangling_link.txt").symlink_to("does-not-exist.txt")

    rich_warning.cache_clear()
    out = build_sdist(str(tmp_path), config_settings=None)

    with tarfile.open(tmp_path / out, "r:gz") as tar:
        link_member = tar.getmember("cmake_example-0.0.1/dangling_link.txt")
        assert link_member.issym(), (
            "A dangling symlink should be stored as a symlink, not dereferenced"
        )

    err = capsys.readouterr().err
    assert "dangling_link.txt" in err
    assert "sdist.resolve-symlinks" in err


@pytest.mark.usefixtures("package_simple_pyproject_ext", "can_symlink")
def test_pep517_sdist_dangling_external_symlink(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    In "external" mode, an escaping symlink is normally dereferenced; a
    dangling one cannot be, so it must be stored as a symlink member instead
    of crashing.
    """
    Path("dangling_ext.txt").symlink_to(tmp_path / "outside" / "gone.txt")

    rich_warning.cache_clear()
    out = build_sdist(
        str(tmp_path), config_settings={"sdist.resolve-symlinks": "external"}
    )

    with tarfile.open(tmp_path / out, "r:gz") as tar:
        link_member = tar.getmember("cmake_example-0.0.1/dangling_ext.txt")
        assert link_member.issym(), (
            "A dangling external symlink should be stored as a symlink"
        )

    err = capsys.readouterr().err
    assert "dangling_ext.txt" in err
