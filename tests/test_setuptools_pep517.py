from __future__ import annotations

import importlib.metadata
import sys
import tarfile
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest
import setuptools
from conftest import VEnv
from packaging.version import Version

from scikit_build_core._compat.setuptools.errors import SetupError
from scikit_build_core.setuptools import build_cmake, wrapper
from scikit_build_core.setuptools import build_meta as setuptools_build_meta
from scikit_build_core.setuptools.build_meta import build_sdist, build_wheel

try:
    from vcs_versioning.overrides import GlobalOverrides
except ImportError:  # pragma: no cover - setuptools-scm < 10 or missing dependency
    GlobalOverrides = None  # type: ignore[assignment, misc]

pytestmark = pytest.mark.setuptools
setuptools_version = Version(importlib.metadata.version("setuptools"))
build_editable = getattr(setuptools_build_meta, "build_editable", None)


@dataclass(frozen=True)
class SetuptoolsInstallDirCase:
    package: str
    module: str
    wheel_prefix: str
    editable_dir: Path
    wheel_missing: str | None = None


SETUPTOOLS_INSTALL_DIR_CASES = [
    SetuptoolsInstallDirCase(
        package="plugin_setuptools_install_dir",
        module="plugin_example",
        wheel_prefix="plugin_example",
        editable_dir=Path("src/plugin_example"),
    ),
    SetuptoolsInstallDirCase(
        package="wrapper_setuptools_install_dir",
        module="wrapper_example",
        wheel_prefix="wrapper_example",
        editable_dir=Path("src/wrapper_example"),
        wheel_missing="src/wrapper_example/__init__.py",
    ),
]

SETUPTOOLS_INSTALL_DIR_CASE_IDS = ["plugin", "wrapper"]


def _assert_extension_import(venv: VEnv, module: str) -> None:
    add = venv.execute(f"import {module}; print({module}.add(1, 2))")
    assert add.strip() == "3"


@pytest.fixture(autouse=True)
def setuptools_scm_overrides():
    if GlobalOverrides is None:
        yield
        return

    with GlobalOverrides.from_env("SETUPTOOLS_SCM"):
        yield


@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package")
def test_pep517_sdist(tmp_path: Path):
    correct_metadata = textwrap.dedent(
        """\
        Name: cmake-example
        Version: 0.0.1
        Requires-Python: >=3.8
        Provides-Extra: test
        """
        # TODO: why is this missing?
        # Requires-Dist: pytest>=6.0; extra == "test"
        # This was removed in https://github.com/pypa/setuptools/pull/4698 as part of 2.2 support:
        # Metadata-Version: 2.1
    )
    metadata_set = set(correct_metadata.strip().splitlines())

    dist = tmp_path / "dist"
    out = build_sdist(str(dist))

    (sdist,) = dist.iterdir()
    sdist = sdist.resolve()  # Windows mingw64 and UCRT now requires this
    assert sdist.name in {"cmake-example-0.0.1.tar.gz", "cmake_example-0.0.1.tar.gz"}
    assert sdist == dist / out
    cmake_example = sdist.name[:13]

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names == {
            f"{cmake_example}-0.0.1/{x}"
            for x in (
                # TODO: "CMakeLists.txt",
                "PKG-INFO",
                "src",
                "src/cmake_example.egg-info",
                "src/cmake_example.egg-info/PKG-INFO",
                "src/cmake_example.egg-info/SOURCES.txt",
                "src/cmake_example.egg-info/dependency_links.txt",
                "src/cmake_example.egg-info/not-zip-safe",
                "src/cmake_example.egg-info/requires.txt",
                "src/cmake_example.egg-info/top_level.txt",
                "pyproject.toml",
                "setup.cfg",
                "setup.py",
                "LICENSE",
                # TODO: "src/main.c",
            )
        } | {f"{cmake_example}-0.0.1"}
        pkg_info = f.extractfile(f"{cmake_example}-0.0.1/PKG-INFO")
        assert pkg_info
        pkg_info_contents = set(pkg_info.read().decode().strip().splitlines())
        assert metadata_set <= pkg_info_contents


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.broken_on_urct
@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package")
def test_pep517_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert len(file_names) == 2
    assert "cmake_example-0.0.1.dist-info" in file_names
    file_names.remove("cmake_example-0.0.1.dist-info")
    (so_file,) = file_names

    assert so_file.startswith("cmake_example")
    print("SOFILE:", so_file)

    virtualenv.install(wheel)

    version = virtualenv.execute(
        "import cmake_example; print(cmake_example.__version__)"
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add.strip() == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.broken_on_urct
@pytest.mark.skipif(
    build_editable is None, reason="Requires setuptools editable support"
)
@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package")
def test_pep517_editable(virtualenv, tmp_path: Path):
    assert build_editable is not None
    dist = tmp_path / "dist"
    out = build_editable(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-0.editable-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert file_names == {
        "__editable__.cmake_example-0.0.1.pth",
        "cmake_example-0.0.1.dist-info",
    }

    virtualenv.install(wheel)

    module_dir = virtualenv.execute(
        "import pathlib, cmake_example; print(pathlib.Path(cmake_example.__file__).resolve().parent)"
    )
    assert Path(module_dir) == Path("src").resolve()

    version = virtualenv.execute(
        "import cmake_example; print(cmake_example.__version__)"
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add.strip() == "3"


@pytest.mark.parametrize("package", ["toml_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package")
@pytest.mark.skipif(
    setuptools_version < Version("61.0"), reason="Requires setuptools 61+"
)
def test_toml_sdist(tmp_path: Path):
    correct_metadata = textwrap.dedent(
        """\
        Name: cmake-example
        Version: 0.0.1
        Requires-Python: >=3.8
        """
        # This was removed in https://github.com/pypa/setuptools/pull/4698 as part of 2.2 support:
        # Metadata-Version: 2.1
    )
    metadata_set = set(correct_metadata.strip().splitlines())

    dist = tmp_path / "dist"
    out = build_sdist(str(dist))

    (sdist,) = dist.iterdir()
    sdist = sdist.resolve()  # Windows mingw64 and UCRT now requires this
    assert sdist.name in {"cmake-example-0.0.1.tar.gz", "cmake_example-0.0.1.tar.gz"}
    assert sdist == dist / out
    cmake_example = sdist.name[:13]

    with tarfile.open(sdist) as f:
        file_names = set(f.getnames())
        assert file_names == {
            f"{cmake_example}-0.0.1/{x}"
            for x in (
                # TODO: "CMakeLists.txt",
                "PKG-INFO",
                "src",
                "src/cmake_example.egg-info",
                "src/cmake_example.egg-info/PKG-INFO",
                "src/cmake_example.egg-info/SOURCES.txt",
                "src/cmake_example.egg-info/dependency_links.txt",
                "src/cmake_example.egg-info/top_level.txt",
                "pyproject.toml",
                "setup.cfg",
                "LICENSE",
                # TODO: "src/main.c",
            )
        } | {f"{cmake_example}-0.0.1"}
        pkg_info = f.extractfile(f"{cmake_example}-0.0.1/PKG-INFO")
        assert pkg_info
        pkg_info_contents = set(pkg_info.read().decode().strip().splitlines())
        assert metadata_set <= pkg_info_contents


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["toml_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package")
@pytest.mark.skipif(
    setuptools_version < Version("61.0"), reason="Requires setuptools 61+"
)
def test_toml_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert len(file_names) == 2
    assert "cmake_example-0.0.1.dist-info" in file_names
    file_names.remove("cmake_example-0.0.1.dist-info")
    (so_file,) = file_names

    assert so_file.startswith("cmake_example")
    print("SOFILE:", so_file)

    virtualenv.install(wheel)

    version = virtualenv.execute(
        "import cmake_example; print(cmake_example.__version__)"
    )
    assert version.strip() == "0.0.1"

    add = virtualenv.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add.strip() == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["mixed_setuptools"], indirect=True)
@pytest.mark.usefixtures("package")
def test_mixed_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("mixed_setuptools-3.1.4-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = {Path(n).parts[0] for n in zf.namelist()}

    assert len(file_names) == 2
    assert "mixed_setuptools-3.1.4.dist-info" in file_names
    file_names.remove("mixed_setuptools-3.1.4.dist-info")
    (so_file,) = file_names

    assert so_file.startswith("mixed_setuptools")
    print("SOFILE:", so_file)

    virtualenv.install(wheel)

    add = virtualenv.execute(
        "import mixed_setuptools; print(mixed_setuptools.add(1, 2))"
    )
    assert add.strip() == "3"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    reason="Cygwin fails here with ld errors",
    strict=False,
)
@pytest.mark.parametrize(
    ("package", "case"),
    [(case.package, case) for case in SETUPTOOLS_INSTALL_DIR_CASES],
    indirect=["package"],
    ids=SETUPTOOLS_INSTALL_DIR_CASE_IDS,
)
def test_cmake_install_dir_wheel(
    package, case: SetuptoolsInstallDirCase, tmp_path: Path
):
    assert package.name == case.package

    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    wheel = (dist / out).resolve()
    assert wheel.name.startswith(f"{case.wheel_prefix}-0.0.1-")

    with zipfile.ZipFile(wheel) as zf:
        file_names = set(zf.namelist())

    assert f"{case.module}/__init__.py" in file_names
    assert any(name.startswith(f"{case.module}/_core.") for name in file_names)
    if case.wheel_missing is not None:
        assert case.wheel_missing not in file_names

    venv = VEnv(tmp_path / "wheel-venv")
    venv.install(str(wheel))
    _assert_extension_import(venv, case.module)


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    reason="Cygwin fails here with ld errors",
    strict=False,
)
@pytest.mark.parametrize(
    "package", ["wrapper_setuptools_classic_layout"], indirect=True
)
@pytest.mark.usefixtures("package")
def test_wrapper_classic_layout_wheel(tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    wheel = (dist / out).resolve()

    with zipfile.ZipFile(wheel) as zf:
        file_names = set(zf.namelist())

    assert "classic_layout_example/__init__.py" in file_names
    assert any(name.startswith("classic_layout_example/_core.") for name in file_names)
    assert any(
        name.endswith(".data/data/include/classic_layout_example/example.h")
        for name in file_names
    )
    assert not any(
        name.startswith("python/classic_layout_example/") for name in file_names
    )
    assert not any(name.startswith("include/") for name in file_names)

    venv = VEnv(tmp_path / "classic-layout-venv")
    venv.install(str(wheel))
    _assert_extension_import(venv, "classic_layout_example")


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.skipif(
    build_editable is None, reason="Requires setuptools editable support"
)
@pytest.mark.xfail(
    sys.platform.startswith("cygwin"),
    reason="Cygwin fails here with ld errors",
    strict=False,
)
@pytest.mark.parametrize(
    ("package", "case"),
    [(case.package, case) for case in SETUPTOOLS_INSTALL_DIR_CASES],
    indirect=["package"],
    ids=SETUPTOOLS_INSTALL_DIR_CASE_IDS,
)
def test_cmake_install_dir_editable(
    package, case: SetuptoolsInstallDirCase, tmp_path: Path
):
    assert build_editable is not None
    assert package.name == case.package

    dist = tmp_path / "dist"
    out = build_editable(str(dist))
    wheel = (dist / out).resolve()
    assert wheel.name.startswith(f"{case.wheel_prefix}-0.0.1-0.editable-")

    venv = VEnv(tmp_path / "editable-venv")
    venv.install(wheel)

    module_dir = venv.execute(
        f"import pathlib, {case.module}; print(pathlib.Path({case.module}.__file__).resolve().parent)"
    )
    assert Path(module_dir) == (package.workdir / case.editable_dir).resolve()
    _assert_extension_import(venv, case.module)


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.broken_on_urct
@pytest.mark.parametrize("package", ["simple_setuptools_ext"], indirect=True)
@pytest.mark.usefixtures("package")
def test_manifest_hook_wheel(virtualenv, tmp_path: Path):
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("cmake_example-0.0.1-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    with zipfile.ZipFile(wheel) as zf:
        file_names = set(zf.namelist())

    assert "LICENSE" not in file_names
    assert any(Path(name).stem.startswith("cmake_example") for name in file_names)

    virtualenv.install(wheel)
    add = virtualenv.execute("import cmake_example; print(cmake_example.add(1, 2))")
    assert add.strip() == "3"


@pytest.mark.parametrize("wrapper_compat", [True, False], ids=["wrapper", "plugin"])
def test_skbuild_configure_and_build_options(
    wrapper_compat: bool, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    # Classic scikit-build compatibility env vars, honored only by the wrapper
    # (scikit_build_core.setuptools.wrapper.setup), not the general plugin.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "CMakeLists.txt").touch()
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("SKBUILD_CONFIGURE_OPTIONS", "-DFOO=ON -DBAR='a b'")
    monkeypatch.setenv("SKBUILD_BUILD_OPTIONS", "-- -l4")

    captured: dict[str, list[str]] = {}

    class StopRunError(Exception):
        pass

    class FakeConfig:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.env: dict[str, str] = {}
            self.build_type = "Release"

    class FakeBuilder:
        def __init__(self, *, config: object, **_kwargs: object) -> None:
            self.config = config

        def get_cmake_args(self) -> list[str]:
            return []

        def configure(self, *, configure_args: list[str], **_kwargs: object) -> None:
            captured["configure"] = list(configure_args)

        def build(self, *, build_args: list[str]) -> None:
            captured["build"] = list(build_args)
            raise StopRunError

    monkeypatch.setattr(
        "scikit_build_core.cmake.CMake.default_search",
        classmethod(lambda *_args, **_kwargs: object()),
    )
    monkeypatch.setattr(build_cmake, "CMaker", FakeConfig)
    monkeypatch.setattr(build_cmake, "Builder", FakeBuilder)

    dist = setuptools.Distribution({"name": "x", "version": "0.0.1"})
    if wrapper_compat:
        setattr(dist, build_cmake.WRAPPER_COMPAT, True)
    cmd = build_cmake.BuildCMake(dist)
    cmd.initialize_options()
    cmd.build_lib = str(tmp_path / "build")
    cmd.build_temp = str(tmp_path / "tmp")
    cmd.plat_name = "linux-x86_64"
    cmd.source_dir = "."
    cmd.cmake_args = ["-DDIST=1"]

    with pytest.raises(StopRunError):
        cmd.run()

    if wrapper_compat:
        assert captured["configure"] == ["-DDIST=1", "-DFOO=ON", "-DBAR=a b"]
        assert captured["build"] == ["--", "-l4"]
    else:
        assert captured["configure"] == ["-DDIST=1"]
        assert captured["build"] == []


def test_manifest_hook_must_be_callable():
    with pytest.raises(
        SetupError,
        match="cmake_process_manifest_hook must be callable",
    ):
        build_cmake.cmake_process_manifest_hook(
            setuptools.Distribution(),
            "cmake_process_manifest_hook",
            object(),  # type: ignore[arg-type]
        )


def test_validate_settings_raises_setup_error():
    # Must use a real exception (not bare assert) so it survives python -O.
    settings = build_cmake._load_settings()
    settings.wheel.py_api = "cp39"
    with pytest.raises(SetupError, match=r"wheel\.py_api is not supported"):
        build_cmake._validate_settings(settings)


def test_wrapper_setup_raises_setup_error():
    with pytest.raises(SetupError, match="cmake_with_sdist not supported"):
        wrapper.setup(cmake_with_sdist=True)


def test_cmake_install_target_keyword_validates_type():
    with pytest.raises(SetupError, match="cmake_install_target must be a string"):
        build_cmake.cmake_install_target(
            setuptools.Distribution(),
            "cmake_install_target",
            object(),  # type: ignore[arg-type]
        )


def test_cmake_install_target_maps_to_install_targets():
    settings = build_cmake._load_settings()
    settings.install.targets = ["existing"]
    dist = setuptools.Distribution()
    dist.cmake_install_target = "install-distribution"  # type: ignore[attr-defined]
    build_cmake._apply_cmake_install_target(settings, dist)
    assert settings.install.targets == ["existing", "install-distribution"]


@pytest.mark.parametrize("target", [None, "install"])
def test_cmake_install_target_default_is_noop(target):
    settings = build_cmake._load_settings()
    dist = setuptools.Distribution()
    if target is not None:
        dist.cmake_install_target = target  # type: ignore[attr-defined]
    build_cmake._apply_cmake_install_target(settings, dist)
    assert settings.install.targets == []


def test_load_settings_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        textwrap.dedent(
            """\
            [tool.scikit-build]
            wheel.cmake = false

            [[tool.scikit-build.overrides]]
            if.state = "editable"
            wheel.cmake = true
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    # Default state is sdist, so the editable override should not apply.
    assert build_cmake._load_settings().wheel.cmake is False
    assert build_cmake._load_settings(state="wheel").wheel.cmake is False
    assert build_cmake._load_settings(state="editable").wheel.cmake is True


def test_wrapper_forwards_manifest_hook(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    # Without a CMakeLists.txt, the wrapper skips CMake entirely
    (tmp_path / "CMakeLists.txt").touch()
    monkeypatch.chdir(tmp_path)

    dist = setuptools.Distribution()

    def passthrough_hook(cmake_manifest: list[str]) -> list[str]:
        return cmake_manifest

    def fake_setup(**kwargs: object) -> setuptools.Distribution:
        assert kwargs["cmake_process_manifest_hook"] is passthrough_hook
        return dist

    monkeypatch.setattr(setuptools, "setup", fake_setup)

    assert (
        wrapper.setup(
            cmake_source_dir=".",
            cmake_process_manifest_hook=passthrough_hook,
        )
        is dist
    )
