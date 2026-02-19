from __future__ import annotations

import contextlib
import dataclasses
import importlib.util
import os
import shutil
import subprocess
import sys
import sysconfig
from collections.abc import Iterable
from importlib import metadata
from pathlib import Path
from typing import Any, Literal, overload

import packaging.tags
import packaging.utils
import virtualenv as _virtualenv
from filelock import FileLock

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

if sys.version_info < (3, 10):
    from typing_extensions import TypeGuard
else:
    from typing import TypeGuard


import download_wheels
import pytest
from packaging.requirements import Requirement
from packaging.version import Version

DIR = Path(__file__).parent.resolve()
BASE = DIR.parent

VIRTUALENV_VERSION = Version(metadata.version("virtualenv"))


def _is_valid_wheel(wheel: Path) -> bool:
    _, _, _, tags = packaging.utils.parse_wheel_filename(wheel.name)
    supported = set(packaging.tags.sys_tags())
    return any(tag in supported for tag in tags)


@pytest.fixture(scope="session")
def pep518_wheelhouse(
    pytestconfig: pytest.Config, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    wheelhouse = pytestconfig.cache.mkdir("wheelhouse")
    tmp_path = tmp_path_factory.mktemp("wheelhouse_tmp")

    main_lock = FileLock(wheelhouse / "main.lock")
    with main_lock:
        if not list(tmp_path.glob("scikit_build_core-*.whl")):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--wheel-dir",
                    f"{tmp_path}",
                    "--no-build-isolation",
                    f"{BASE}",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            for wheel in tmp_path.glob("*.whl"):
                shutil.copy(wheel, wheelhouse)

    wheels_lock = FileLock(wheelhouse / "wheels.lock")
    with wheels_lock:
        if not all(
            any(_is_valid_wheel(whl) for whl in wheelhouse.glob(f"{p}*.whl"))
            for p in download_wheels.WHEELS
        ):
            download_wheels.prepare(wheelhouse)

    return wheelhouse


class VEnv:
    def __init__(self, env_dir: Path, *, wheelhouse: Path | None = None) -> None:
        cmd = [str(env_dir), "--no-setuptools", "--activators", ""]
        if Version("20.31.0") > VIRTUALENV_VERSION:
            cmd.append("--no-wheel")
        result = _virtualenv.cli_run(cmd, setup_logging=False)
        self.wheelhouse = wheelhouse
        self.executable = Path(result.creator.exe)
        self.env_dir = env_dir.resolve()
        self.platlib = Path(
            self.execute("import sysconfig; print(sysconfig.get_path('platlib'))")
        )
        self.purelib = Path(
            self.execute("import sysconfig; print(sysconfig.get_path('purelib'))")
        )

    @overload
    def run(self, *args: str, capture: Literal[True]) -> str: ...

    @overload
    def run(self, *args: str, capture: Literal[False] = ...) -> None: ...

    def run(self, *args: str, capture: bool = False) -> str | None:
        __tracebackhide__ = True
        env = os.environ.copy()
        paths = {str(self.executable.parent)}
        env["PATH"] = os.pathsep.join([*paths, env["PATH"]])
        env["VIRTUAL_ENV"] = str(self.env_dir)
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "ON"
        if self.wheelhouse is not None:
            env["PIP_NO_INDEX"] = "ON"
            env["PIP_FIND_LINKS"] = str(self.wheelhouse)

        str_args = [os.fspath(a) for a in args]

        # Windows does not make a python shortcut in venv
        if str_args[0] in {"python", "python3"}:
            str_args[0] = str(self.executable)

        if capture:
            result = subprocess.run(
                str_args,
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                print(result.stdout, file=sys.stdout)
                print(result.stderr, file=sys.stderr)
                print("FAILED RUN:", *str_args, file=sys.stderr)
                raise SystemExit(result.returncode)
            return result.stdout.strip()

        result_bytes = subprocess.run(
            str_args,
            check=False,
            env=env,
        )
        if result_bytes.returncode != 0:
            print("FAILED RUN:", *str_args, file=sys.stderr)
            raise SystemExit(result_bytes.returncode)
        return None

    def execute(self, command: str) -> str:
        return self.run(str(self.executable), "-c", command, capture=True)

    def module(self, *args: str) -> None:
        return self.run(str(self.executable), "-m", *args)

    def install(self, *args: str, isolated: bool = True) -> None:
        isolated_flags = "" if isolated else ["--no-build-isolation"]
        self.module("pip", "install", *isolated_flags, *args)

    def prepare_no_build_isolation(self) -> None:
        if not self.wheelhouse:
            msg = "Wheelhouse was not setup."
            raise ValueError(msg)

        ninja = [
            "ninja" for f in self.wheelhouse.iterdir() if f.name.startswith("ninja-")
        ]
        cmake = [
            "cmake" for f in self.wheelhouse.iterdir() if f.name.startswith("cmake-")
        ]

        self.install("pip>23")
        self.install("scikit-build-core", *ninja, *cmake)


@pytest.fixture
def isolated(tmp_path: Path, pep518_wheelhouse: Path) -> VEnv:
    """Isolated virtual environment.

    To control build isolation, see :py:func:`isolate`
    """
    path = tmp_path / "venv"
    return VEnv(path, wheelhouse=pep518_wheelhouse)


@pytest.fixture
def virtualenv(tmp_path: Path) -> VEnv:
    path = tmp_path / "venv"
    return VEnv(path)


@dataclasses.dataclass(frozen=True)
class PackageInfo:
    name: str
    workdir: Path
    sdist_hash38: str | None = None
    sdist_hash39: str | None = None
    sdist_dated_hash39: str | None = None
    sdist_dated_hash38: str | None = None

    @property
    def sdist_hash(self) -> str | None:
        return self.sdist_hash38 if sys.version_info < (3, 9) else self.sdist_hash39

    @property
    def sdist_dated_hash(self) -> str | None:
        return (
            self.sdist_dated_hash38
            if sys.version_info < (3, 9)
            else self.sdist_dated_hash39
        )

    @property
    def source_date_epoch(self) -> str:
        return "12345"


def process_package(
    package: PackageInfo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pkg_src = DIR / "packages" / package.name
    assert pkg_src.exists()
    shutil.copytree(pkg_src, package.workdir, dirs_exist_ok=True)
    monkeypatch.chdir(package.workdir)


@pytest.fixture
def package(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> PackageInfo:
    """Get the test package.

    Parameterize this fixture with the package name in the tests/packages directory.
    (Use ``indirect=True`` to pass the parameterization value to the fixture instead of
    directly to the test function.)
    https://docs.pytest.org/en/stable/example/parametrize.html#indirect-parametrization
    """
    pkg_name = request.param
    assert isinstance(pkg_name, str)
    package = PackageInfo(pkg_name, tmp_path_factory.mktemp("pkg"))
    assert (DIR / "packages" / package.name).exists()
    process_package(package, monkeypatch)
    return package


@pytest.fixture
def multiple_packages(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> list[PackageInfo]:
    package_names = request.param
    assert isinstance(package_names, Iterable)
    packages = []
    for pkg_name in package_names:
        pkg = PackageInfo(pkg_name, tmp_path_factory.mktemp("pkg"))
        process_package(pkg, monkeypatch)
        packages.append(pkg)
    monkeypatch.chdir(tmp_path_factory.getbasetemp())
    return packages


@pytest.fixture
def package_simple_pyproject_ext(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> PackageInfo:
    package = PackageInfo(
        "simple_pyproject_ext",
        tmp_path_factory.mktemp("pkg"),
        "71b4e95854ef8d04886758d24d18fe55ebe63648310acf58c7423387cca73508",
        "ed930179fbf5adc2e71a64a6f9686c61fdcce477c85bc94dd51598641be886a7",
        "0178462b64b4eb9c41ae70eb413a9cc111c340e431b240af1b218fe81b0c2ecb",
        "de79895a9d5c2112257715214ab419d3635e841716655e8a55390e5d52445819",
    )
    process_package(package, monkeypatch)
    return package


@dataclasses.dataclass(frozen=True)
class Isolate:
    """Selection for build isolation."""

    state: bool
    flags: list[str]


@pytest.fixture(params=[True, False], ids=["isolated", "not_isolated"])
def isolate(request: pytest.FixtureRequest, isolated: VEnv) -> Isolate:
    """Control build isolation.

    For an isolated virtual environment, see :py:func:`isolated`
    """
    isolate_request = request.param
    assert isinstance(isolate_request, bool)
    if not isolate_request:
        isolated.prepare_no_build_isolation()
    flags = []
    if not isolate_request:
        flags.append("--no-build-isolation")
    return Isolate(
        state=isolate_request,
        flags=flags,
    )


def is_editable_mode(maybe_mode: str) -> TypeGuard[Literal["redirect", "inplace"]]:
    return maybe_mode in {"redirect", "inplace"}


@dataclasses.dataclass(frozen=True)
class Editable:
    mode: Literal["redirect", "inplace"] | None
    config_settings: list[str]

    @property
    def flags(self) -> list[str]:
        if not self.mode:
            return self.config_settings
        return [*self.config_settings, "-e"]


@pytest.fixture(params=[pytest.param(None, id="not_editable"), "redirect", "inplace"])
def editable(request: pytest.FixtureRequest) -> Editable:
    editable_mode = request.param
    assert editable_mode is None or is_editable_mode(editable_mode)
    config_settings = []
    if editable_mode:
        config_settings.append(f"--config-settings=editable.mode={editable_mode}")
        if editable_mode != "inplace":
            build_dir = "build/{wheel_tag}"
            config_settings.append(f"--config-settings=build-dir={build_dir}")
    return Editable(
        mode=editable_mode,
        config_settings=config_settings,
    )


def which_mock(name: str) -> str | None:
    if name in {"ninja", "ninja-build", "cmake3", "samu", "gmake", "make"}:
        return None
    if name == "cmake":
        return "cmake/path"
    return None


@pytest.fixture
def protect_get_requires(fp, monkeypatch):
    """
    Protect get_requires from actually calling anything variable during tests.
    """
    # This needs to be passed due to packaging.tags 22 extra checks if macos 10.16 is reported
    fp.pass_command([sys.executable, fp.any()])
    monkeypatch.setattr(shutil, "which", which_mock)
    monkeypatch.delenv("CMAKE_GENERATOR", raising=False)

    orig_find_spec = importlib.util.find_spec

    def find_spec(name: str, package: str | None = None) -> Any:
        if name in {"cmake", "ninja"}:
            return None
        return orig_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)


@pytest.fixture
def pybind11():
    return pytest.importorskip("pybind11")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        # Ensure all tests using virtualenv are marked as such
        if "virtualenv" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.virtualenv)
        if "isolated" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.virtualenv)
            item.add_marker(pytest.mark.isolated)
            item.add_marker(pytest.mark.network)


def pytest_report_header() -> str:
    with BASE.joinpath("pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)
    project = pyproject.get("project", {})

    pkgs = project.get("dependencies", [])
    pkgs += [p for ps in project.get("optional-dependencies", {}).values() for p in ps]
    if "name" in project:
        pkgs.append(project["name"])
    interesting_packages = {Requirement(p).name for p in pkgs}
    interesting_packages |= {"pip", "hatch-fancy-pypi-readme", "setuptools-scm"}

    valid = []
    for package in sorted(interesting_packages):
        with contextlib.suppress(ModuleNotFoundError):
            valid.append(f"{package}=={metadata.version(package)}")
    reqs = " ".join(valid)
    lines = [
        f"installed packages of interest: {reqs}",
        f"sysconfig platform: {sysconfig.get_platform()}",
    ]
    return "\n".join(lines)
