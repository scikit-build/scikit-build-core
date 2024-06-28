import sys
import sysconfig
import typing
import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_editable


@pytest.fixture(params=["redirect", "inplace"])
def editable_mode(request: pytest.FixtureRequest) -> str:
    return typing.cast(str, request.param)


# TODO: figure out why gmake is reporting no rule to make simple_pure.cpp
@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    strict=False,
    reason="No idea why this fails on Cygwin",
)
@pytest.mark.usefixtures("package_simplest_c")
def test_pep660_wheel(editable_mode: str):
    dist = Path("dist")
    out = build_editable("dist", {"editable.mode": editable_mode})
    (wheel,) = dist.glob("simplest-0.0.1-*.whl")
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(p).parts[0] for p in zf.namelist()}

        with zf.open("simplest-0.0.1.dist-info/METADATA") as f:
            metadata = f.read().decode("utf-8")

    assert len(file_names) == 4 if editable_mode == "redirect" else 2
    assert "simplest-0.0.1.dist-info" in file_names
    if editable_mode == "redirect":
        assert "simplest" in file_names
        assert "_simplest_editable.py" in file_names
    else:
        assert "simplest" not in file_names
        assert "_simplest_editable.py" not in file_names
    assert "_simplest_editable.pth" in file_names

    assert "Metadata-Version: 2.1" in metadata
    assert "Name: simplest" in metadata
    assert "Version: 0.0.1" in metadata


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
@pytest.mark.parametrize("isolate", [True, False], ids=["isolated", "not_isolated"])
@pytest.mark.usefixtures("package_simplest_c")
def test_pep660_pip_isolated(isolated, isolate, editable_mode: str):
    isolate_args = ["--no-build-isolation"] if not isolate else []
    isolated.install("pip>=23")
    if not isolate:
        isolated.install("scikit-build-core")

    build_dir = "" if editable_mode == "inplace" else "build/{wheel_tag}"

    isolated.install(
        "-v",
        f"--config-settings=build-dir={build_dir}",
        f"--config-settings=editable.mode={editable_mode}",
        *isolate_args,
        "-e",
        ".",
    )

    value = isolated.execute("import simplest; print(simplest.square(2))")
    assert value == "4.0"

    location_str = isolated.execute(
        "import simplest; print(*simplest.__path__, sep=';')"
    )
    locations = [Path(s).resolve() for s in location_str.split(";")]

    # First path is from the python source
    python_source = Path("src/simplest").resolve()
    assert any(x.samefile(python_source) for x in locations)

    cmake_install = isolated.platlib.joinpath("simplest").resolve()
    if editable_mode == "redirect":
        # Second path is from the CMake install
        assert any(x.samefile(cmake_install) for x in locations)

    location = isolated.execute("import simplest; print(simplest.__file__)")
    # The package file is defined in the python source and __file__ must point to it
    assert Path("src/simplest/__init__.py").resolve().samefile(Path(location).resolve())

    location = isolated.execute(
        "import simplest._module; print(simplest._module.__file__)"
    )

    if sys.version_info < (3, 8, 7):
        import distutils.sysconfig  # pylint: disable=deprecated-module

        ext_suffix = distutils.sysconfig.get_config_var("EXT_SUFFIX")
    else:
        ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")

    module_source = python_source if editable_mode == "inplace" else cmake_install
    module_file = module_source / f"_module{ext_suffix}"

    # Windows FindPython may produce the wrong extension
    if (
        sys.version_info < (3, 8, 7)
        and sys.platform.startswith("win")
        and not module_file.is_file()
    ):
        module_file = module_source / "_module.pyd"

    assert module_file.samefile(Path(location).resolve())
