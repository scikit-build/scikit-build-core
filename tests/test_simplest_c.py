import tarfile
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_sdist, build_wheel

from pathutils import contained

DIR = Path(__file__).parent.resolve()
SIMPLEST = DIR / "packages/simplest_c"


def test_pep517_sdist(tmp_path, monkeypatch):
    dist = tmp_path.resolve() / "dist"
    monkeypatch.chdir(SIMPLEST)

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


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize(
    "component", [[], ["PythonModule"], ["PythonModule", "Generated"]]
)
def test_pep517_wheel(tmp_path, monkeypatch, virtualenv, component):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(SIMPLEST)
    out = build_wheel(str(dist), config_settings={"install.components": component})
    (wheel,) = dist.glob("simplest-0.0.1-*.whl")
    assert wheel == dist / out

    virtualenv.install(wheel)

    with zipfile.ZipFile(wheel) as zf:
        file_paths = {Path(n) for n in zf.namelist()}

    file_names = {p.parts[0] for p in file_paths}
    simplest_pkg = {p.name for p in contained(file_paths, "simplest")}
    filtered_pkg = {x for x in simplest_pkg if not x.startswith("_module")}

    if not component or "PythonModule" in component:
        assert filtered_pkg != simplest_pkg
    else:
        assert filtered_pkg == simplest_pkg

    expected_wheel_files = {
        "__init__.py",
        "data.txt",
        "excluded.txt",
        "sdist_only.txt",
    }

    if not component:
        expected_wheel_files.add("generated_ignored.txt")
        expected_wheel_files.add("generated_no_wheel.txt")

    if not component or "Generated" in component:
        expected_wheel_files.add("generated.txt")

    assert len(filtered_pkg) == len(simplest_pkg) - 2
    assert {"simplest-0.0.1.dist-info", "simplest"} == file_names
    assert expected_wheel_files == filtered_pkg
    # Note that generated_ignored.txt is here because all CMake installed files are
    # present, CMake has the final say.

    version = virtualenv.execute("from simplest import square; print(square(2))")
    assert version == "4.0"


@pytest.mark.compile
@pytest.mark.configure
def test_pep517_wheel_incexl(tmp_path, monkeypatch, virtualenv):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.chdir(SIMPLEST)

    out = build_wheel(
        str(dist),
        {
            "sdist.include": "src/simplest/*included*.txt",
            "sdist.exclude": "src/simplest/*excluded*.txt",
            "wheel.exclude": [
                "simplest/sdist_only.txt",
                "simplest/generated_no_wheel.txt",
            ],
            "wheel.packages": ["src/simplest", "src/not_a_package"],
        },
    )

    (wheel,) = dist.glob("simplest-0.0.1-*.whl")
    assert wheel == dist / out

    virtualenv.install(wheel)

    with zipfile.ZipFile(wheel) as zf:
        file_paths = {Path(n) for n in zf.namelist()}
    file_names = {p.parts[0] for p in file_paths}

    simplest_pkg = {x.name for x in contained(file_paths, "simplest")}
    not_a_pkg = {x.name for x in contained(file_paths, "not_a_package")}
    metadata_items = set(contained(file_paths, "simplest-0.0.1.dist-info"))

    assert {
        Path("licenses/LICENSE.txt"),
        Path("metadata_file.txt"),
        Path("RECORD"),
        Path("METADATA"),
        Path("WHEEL"),
    } == metadata_items

    filtered_pkg = {x for x in simplest_pkg if not x.startswith("_module")}

    assert len(filtered_pkg) == len(simplest_pkg) - 2
    assert {"simplest-0.0.1.dist-info", "simplest", "not_a_package"} == file_names
    assert {
        "__init__.py",
        "data.txt",
        "ignored_included.txt",
        "generated.txt",
        "generated_ignored.txt",
    } == filtered_pkg
    assert {"simple.txt"} == not_a_pkg

    version = virtualenv.execute(
        "from simplest import square; print(square(2))",
    )
    assert version == "4.0"
