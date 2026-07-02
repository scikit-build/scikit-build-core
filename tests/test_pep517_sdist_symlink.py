from __future__ import annotations

import sysconfig
import tarfile
from pathlib import Path

import pytest

from scikit_build_core._logging import rich_warning
from scikit_build_core.build import build_sdist

PREFIX = "cmake_example-0.0.1"

# Expected tar member type per resolve-symlinks mode: "reg", "sym", or None
# (absent from the archive). A directory symlink loop cannot be resolved, so
# every mode stores it as a symlink member (on any platform). The
# ext_dir/*_link entries are symlinks nested inside a followed external
# directory: in "external" mode, ones whose target stays inside the followed
# directory are kept as symlinks; ones escaping it must be resolved, even if
# their target lexically lands inside the project when judged against the
# archive path.
EXPECTED = {
    "all": {
        "CMakeLists_link.txt": "reg",
        "src_link": None,
        "src_link/main.cpp": "reg",
        "ext_file.txt": "reg",
        "ext_dir": None,
        "ext_dir/data.txt": "reg",
        "ext_dir/data_link.txt": "reg",
        "ext_dir/esc_link.txt": "reg",
        "ext_dir/sub_link": None,
        "ext_dir/sub_link/sub.txt": "reg",
        "ext_dir/esc_dir": None,
        "ext_dir/esc_dir/esc.txt": "reg",
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
        "ext_dir/data_link.txt": "sym",
        "ext_dir/esc_link.txt": "reg",
        "ext_dir/sub_link": "sym",
        "ext_dir/sub_link/sub.txt": None,
        "ext_dir/esc_dir": None,
        "ext_dir/esc_dir/esc.txt": "reg",
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
        "ext_dir/data_link.txt": None,
        "ext_dir/esc_link.txt": None,
        "ext_dir/sub_link": None,
        "ext_dir/sub_link/sub.txt": None,
        "ext_dir/esc_dir": None,
        "ext_dir/esc_dir/esc.txt": None,
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
        "ext_dir/data_link.txt": "sym",
        "ext_dir/esc_link.txt": "sym",
        "ext_dir/sub_link": None,
        "ext_dir/sub_link/sub.txt": "reg",
        "ext_dir/esc_dir": None,
        "ext_dir/esc_dir/esc.txt": "reg",
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


@pytest.mark.skipif(
    sysconfig.get_platform().startswith(("mingw", "msys")),
    reason="MSYS Python resolves relative symlink targets lexically, so the"
    " nested escaping links read as dangling",
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
    outside.joinpath("secret.txt").write_bytes(b"external secret\n")
    outside.joinpath("escdir").mkdir()
    outside.joinpath("escdir", "esc.txt").write_bytes(b"escaped dir data\n")
    extdir = outside / "extdir"
    extdir.mkdir()
    extdir.joinpath("data.txt").write_bytes(b"external data\n")
    extdir.joinpath("subdir").mkdir()
    extdir.joinpath("subdir", "sub.txt").write_bytes(b"sub data\n")
    # Symlinks nested inside the external directory: two staying inside it,
    # two escaping it (with targets that lexically land inside the project
    # when judged against the archive path ext_dir/...).
    extdir.joinpath("data_link.txt").symlink_to("data.txt")
    extdir.joinpath("esc_link.txt").symlink_to(Path("..") / "secret.txt")
    extdir.joinpath("sub_link").symlink_to("subdir", target_is_directory=True)
    extdir.joinpath("esc_dir").symlink_to(
        Path("..") / "escdir", target_is_directory=True
    )

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
            # Nested symlinks escaping the followed external directory are
            # dereferenced too, judged against the followed link rather than
            # the archive path (which lexically stays inside the project).
            fobj = tar.extractfile(f"{PREFIX}/ext_dir/esc_link.txt")
            assert fobj is not None
            assert fobj.read() == b"external secret\n"
            fobj = tar.extractfile(f"{PREFIX}/ext_dir/esc_dir/esc.txt")
            assert fobj is not None
            assert fobj.read() == b"escaped dir data\n"
            # Nested symlinks staying inside it keep their targets.
            assert members[f"{PREFIX}/ext_dir/data_link.txt"].linkname == "data.txt"
            assert members[f"{PREFIX}/ext_dir/sub_link"].linkname == "subdir"
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
