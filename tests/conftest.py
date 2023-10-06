from __future__ import annotations

import contextlib
import dataclasses
import importlib.util
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import virtualenv as _virtualenv

if sys.version_info < (3, 8):
    import importlib_metadata as metadata
    from typing_extensions import Literal, overload
else:
    from importlib import metadata
    from typing import Literal, overload

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


from typing import TYPE_CHECKING

import pytest
from packaging.requirements import Requirement

if TYPE_CHECKING:
    from collections.abc import Generator

DIR = Path(__file__).parent.resolve()
BASE = DIR.parent


@pytest.fixture(scope="session")
def pep518_wheelhouse(tmp_path_factory: pytest.TempPathFactory) -> Path:
    wheelhouse = tmp_path_factory.mktemp("wheelhouse")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--wheel-dir",
            str(wheelhouse),
            f"{BASE}[pyproject]",
        ],
        check=True,
    )
    packages = [
        "build",
        "hatchling",
        "pip>=23",
        "pybind11",
        "setuptools",
        "virtualenv",
        "wheel",
    ]

    if importlib.util.find_spec("cmake") is not None:
        packages.append("cmake")

    if importlib.util.find_spec("ninja") is not None:
        packages.append("ninja")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "-q",
            "-d",
            str(wheelhouse),
            *packages,
        ],
        check=True,
    )
    return wheelhouse


class VEnv:
    def __init__(self, env_dir: Path, *, wheelhouse: Path | None = None) -> None:
        cmd = [str(env_dir), "--no-setuptools", "--no-wheel", "--activators", ""]
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
    def run(self, *args: str, capture: Literal[True]) -> str:
        ...

    @overload
    def run(self, *args: str, capture: Literal[False] = ...) -> None:
        ...

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


@pytest.fixture()
def isolated(tmp_path: Path, pep518_wheelhouse: Path) -> Generator[VEnv, None, None]:
    path = tmp_path / "venv"
    try:
        yield VEnv(path, wheelhouse=pep518_wheelhouse)
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def virtualenv(tmp_path: Path) -> Generator[VEnv, None, None]:
    path = tmp_path / "venv"
    try:
        yield VEnv(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


@dataclasses.dataclass(frozen=True)
class PackageInfo:
    name: str
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
    package: PackageInfo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package_dir = tmp_path / "pkg"
    shutil.copytree(DIR / "packages" / package.name, package_dir)
    monkeypatch.chdir(package_dir)
    # Just in case this gets littered into the source tree, clear it out
    if Path("dist").is_dir():
        shutil.rmtree("dist")


@pytest.fixture()
def package_simple_pyproject_ext(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> PackageInfo:
    package = PackageInfo(
        "simple_pyproject_ext",
        "c75641407303f3f3a0fd76d24e3d12447b31286fa5d0f687c0f8f8eb804d839f",
        "dc4921bdf694b1b88cb27c8e6128513e174689625447d18c1dd3353348824946",
        "2a135ce826265c5c1c73ebcb603989d8e2f4bca4605ad04c6c82871b5f75840e",
        "7558e1db89e62b0941671796e1a35983a0b50a0701736566ca3ae5dd9ba09846",
    )
    process_package(package, tmp_path, monkeypatch)
    return package


@pytest.fixture()
def package_simple_pyproject_source_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> PackageInfo:
    package = PackageInfo(
        "simple_pyproject_source_dir",
    )
    process_package(package, tmp_path, monkeypatch)
    return package


@pytest.fixture()
def package_simple_setuptools_ext(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> PackageInfo:
    package = PackageInfo("simple_setuptools_ext")
    process_package(package, tmp_path, monkeypatch)
    return package


@pytest.fixture()
def package_mixed_setuptools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> PackageInfo:
    package = PackageInfo("mixed_setuptools")
    process_package(package, tmp_path, monkeypatch)
    return package


@pytest.fixture()
def package_filepath_pure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> PackageInfo:
    package = PackageInfo("filepath_pure")
    process_package(package, tmp_path, monkeypatch)
    return package


@pytest.fixture()
def package_dynamic_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> PackageInfo:
    package = PackageInfo("dynamic_metadata")
    process_package(package, tmp_path, monkeypatch)
    return package


@pytest.fixture()
def package_simplest_c(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PackageInfo:
    package = PackageInfo(
        "simplest_c",
    )
    process_package(package, tmp_path, monkeypatch)
    return package


@pytest.fixture()
def navigate_editable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PackageInfo:
    package = PackageInfo(
        "navigate_editable",
    )
    process_package(package, tmp_path, monkeypatch)
    return package


@pytest.fixture()
def package_sdist_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> PackageInfo:
    package = PackageInfo(
        "sdist_config",
    )
    process_package(package, tmp_path, monkeypatch)
    return package


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
    interesting_packages.add("pip")

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
