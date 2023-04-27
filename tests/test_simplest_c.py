import shutil
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_sdist, build_wheel

DIR = Path(__file__).parent.resolve()
SIMPLEST = DIR / "packages/simplest_c"


def test_pep517_sdist(tmp_path, monkeypatch):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(SIMPLEST)
    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_sdist(str(dist))

    (sdist,) = dist.iterdir()
    assert sdist.name == "simplest-0.0.1.tar.gz"
    assert sdist == dist / out

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names == {
            f"simplest-0.0.1/{x}"
            for x in (
                "CMakeLists.txt",
                "pyproject.toml",
                ".gitignore",
                "src/module.c",
                "src/simplest/__init__.py",
                "src/simplest/_module.pyi",
                "src/simplest/data.txt",
                "src/simplest/sdist_only.txt",
                "src/not_a_package/simple.txt",
                "src/simplest/excluded.txt",
                "PKG-INFO",
            )
        }


@pytest.mark.compile()
@pytest.mark.configure()
def test_pep517_wheel(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(SIMPLEST)
    if Path("dist").is_dir():
        shutil.rmtree("dist")
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("simplest-0.0.1-*.whl")
    assert wheel == dist / out

    virtualenv.install(wheel)

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = {x.name for x in p.iterdir()}
            simplest_pkg = {x.name for x in p.joinpath("simplest").iterdir()}

        filtered_pkg = {x for x in simplest_pkg if not x.startswith("_module")}

        assert len(filtered_pkg) == len(simplest_pkg) - 2
        assert {"simplest-0.0.1.dist-info", "simplest"} == file_names
        assert {
            "__init__.py",
            "data.txt",
            "excluded.txt",
            "generated.txt",
            "sdist_only.txt",
            "generated_ignored.txt",
        } == filtered_pkg
        # Note that generated_ignored.txt is here because all CMake installed files are
        # present, CMake has the final say.

    version = virtualenv.execute("from simplest import square; print(square(2))")
    assert version == "4.0"


@pytest.mark.compile()
@pytest.mark.configure()
def test_pep517_wheel_incexl(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(SIMPLEST)
    if Path("dist").is_dir():
        shutil.rmtree("dist")

    out = build_wheel(
        str(dist),
        {
            "sdist.include": "src/simplest/*included*.txt",
            "sdist.exclude": "src/simplest/*excluded*.txt",
            "wheel.packages": ["src/simplest", "src/not_a_package"],
        },
    )

    (wheel,) = dist.glob("simplest-0.0.1-*.whl")
    assert wheel == dist / out

    virtualenv.install(wheel)

    if sys.version_info >= (3, 8):
        with wheel.open("rb") as f:
            p = zipfile.Path(f)
            file_names = {x.name for x in p.iterdir()}
            simplest_pkg = {x.name for x in p.joinpath("simplest").iterdir()}
            not_a_pkg = {x.name for x in p.joinpath("not_a_package").iterdir()}

        filtered_pkg = {x for x in simplest_pkg if not x.startswith("_module")}

        assert len(filtered_pkg) == len(simplest_pkg) - 2
        assert {"simplest-0.0.1.dist-info", "simplest", "not_a_package"} == file_names
        assert {
            "__init__.py",
            "data.txt",
            "ignored_included.txt",
            "generated.txt",
            "sdist_only.txt",
            "generated_ignored.txt",
        } == filtered_pkg
        assert {"simple.txt"} == not_a_pkg

    version = virtualenv.execute(
        "from simplest import square; print(square(2))",
    )
    assert version == "4.0"
