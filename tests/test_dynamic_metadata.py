from __future__ import annotations

import importlib
import importlib.metadata
import shutil
import subprocess
import textwrap
import types
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

from scikit_build_core._compat import tomllib
from scikit_build_core._vendor import pyproject_metadata
from scikit_build_core.build import build_wheel
from scikit_build_core.build.metadata import get_standard_metadata
from scikit_build_core.builder.get_requires import GetRequires
from scikit_build_core.metadata import regex
from scikit_build_core.settings.skbuild_read_settings import SettingsReader

from pathutils import contained

if TYPE_CHECKING:
    from typing import Literal


# these are mock plugins returning known results
# it turns out to be easier to create EntryPoint objects pointing to real
# functions than to mock them.
def ep_version(
    field: str,
    _settings: dict[str, object] | None = None,
) -> str:
    assert field == "version"
    return "0.0.2"


def ep_readme(
    field: str,
    _settings: dict[str, object] | None = None,
) -> str | dict[str, str | None]:
    assert field == "readme"
    return {
        "content-type": "text/x-rst",
        "text": "Some text",
    }


def ep_license(
    field: str,
    _settings: dict[str, object] | None = None,
) -> dict[str, str | None]:
    assert field == "license"
    return {"text": "MIT License"}


def ep_dual(
    _field: str,
    _settings: dict[str, object] | None = None,
) -> str | dict[str, str | None]:
    # Fields intentionally not checked to verify backend error thrown
    if _field == "version":
        return "0.3"
    if _field == "license":
        return {"text": "BSD License"}
    msg = f"Invalid field {_field}"
    raise KeyError(msg)


original_loader = importlib.import_module


def special_loader(name: str, *args: Any, **kwargs: Any) -> Any:
    if name == "test_version":
        test_version = types.ModuleType("test_version")
        test_version.dynamic_metadata = ep_version  # type: ignore[attr-defined]
        return test_version
    if name == "test_readme":
        test_readme = types.ModuleType("test_readme")
        test_readme.dynamic_metadata = ep_readme  # type: ignore[attr-defined]
        return test_readme
    if name == "test_license":
        test_license = types.ModuleType("test_license")
        test_license.dynamic_metadata = ep_license  # type: ignore[attr-defined]
        return test_license
    if name == "test_dual":
        test_dual = types.ModuleType("test_dual")
        test_dual.dynamic_metadata = ep_dual  # type: ignore[attr-defined]
        return test_dual

    return original_loader(name, *args, **kwargs)


@pytest.fixture
def mock_entry_points(monkeypatch):
    monkeypatch.setattr(importlib, "import_module", special_loader)


@pytest.mark.parametrize("package", ["dynamic_metadata"], indirect=True)
@pytest.mark.usefixtures("mock_entry_points", "package")
def test_dynamic_metadata():
    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)

    assert str(metadata.version) == "0.0.2"
    assert metadata.license == pyproject_metadata.License("MIT License", None)
    assert metadata.readme == pyproject_metadata.Readme("Some text", None, "text/x-rst")


@pytest.mark.parametrize("source", ["plugin_project.toml", "plugin_array_project.toml"])
@pytest.mark.parametrize("package", ["dynamic_metadata"], indirect=True)
@pytest.mark.usefixtures("package")
def test_plugin_metadata(source):
    reason_msg = (
        "install hatch-fancy-pypi-readme and setuptools-scm to test the "
        "dynamic metadata plugins"
    )
    pytest.importorskip("hatch_fancy_pypi_readme", reason=reason_msg)
    pytest.importorskip("setuptools_scm", reason=reason_msg)
    if shutil.which("git") is None:
        pytest.skip("git is not installed")

    hfpr_version = Version(importlib.metadata.version("hatch_fancy_pypi_readme"))

    shutil.copy(source, "pyproject.toml")

    subprocess.run(["git", "init", "--initial-branch=main"], check=True)
    subprocess.run(["git", "config", "user.name", "bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@scikit-build.org"], check=True)
    subprocess.run(["git", "add", "pyproject.toml"], check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], check=True)
    subprocess.run(["git", "tag", "v0.1.0", "-m", "initial commint"], check=True)

    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)

    assert str(metadata.version) == "0.1.0"
    if hfpr_version >= Version("25.1"):
        assert metadata.readme == pyproject_metadata.Readme(
            "Fragment #1Fragment #2 -- 0.1.0Fragment #3 -- fancy", None, "text/x-rst"
        )
    else:
        assert metadata.readme == pyproject_metadata.Readme(
            "Fragment #1Fragment #2 -- 0.1.0Fragment #3 -- $HFPR_PACKAGE_NAME",
            None,
            "text/x-rst",
        )

    assert set(GetRequires().dynamic_metadata()) == {
        "hatch-fancy-pypi-readme>=23.2",
        "setuptools-scm",
    }

    assert metadata.optional_dependencies == {"dev": [Requirement("fancy==0.1.0")]}


@pytest.mark.parametrize("package", ["dynamic_metadata"], indirect=True)
@pytest.mark.usefixtures("package")
def test_faulty_metadata():
    reason_msg = "install hatch-fancy-pypi-readme to test the dynamic metadata plugins"
    pytest.importorskip("hatch_fancy_pypi_readme", reason=reason_msg)

    with Path("faulty_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.raises(KeyError):
        get_standard_metadata(pyproject, settings)


@pytest.mark.parametrize("package", ["dynamic_metadata"], indirect=True)
@pytest.mark.usefixtures("package")
def test_local_plugin_metadata():
    with Path("local_pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)
    assert metadata.version == Version("3.2.1")


@pytest.mark.parametrize("package", ["dynamic_metadata"], indirect=True)
@pytest.mark.usefixtures("package")
def test_warn_metadata():
    with Path("warn_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.raises(ModuleNotFoundError):
        get_standard_metadata(pyproject, settings)


@pytest.mark.parametrize("package", ["dynamic_metadata"], indirect=True)
@pytest.mark.usefixtures("package")
def test_fail_experimental_metadata():
    with Path("warn_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(
        pyproject, {"experimental": "false"}, state="metadata_wheel"
    )

    with pytest.raises(SystemExit) as exc:
        settings_reader.validate_may_exit()
    (value,) = exc.value.args
    assert value == 7


@pytest.mark.parametrize("package", ["dynamic_metadata"], indirect=True)
@pytest.mark.usefixtures("mock_entry_points", "package")
def test_dual_metadata():
    with Path("dual_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    metadata = get_standard_metadata(pyproject, settings)
    assert str(metadata.version) == "0.3"
    assert metadata.license == pyproject_metadata.License("BSD License", None)

    with Path("faulty_dual_project.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings_reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    settings = settings_reader.settings

    settings_reader.validate_may_exit()

    with pytest.raises(KeyError):
        get_standard_metadata(pyproject, settings)


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("package", ["dynamic_metadata"], indirect=True)
@pytest.mark.usefixtures("mock_entry_points", "package")
def test_pep517_wheel(virtualenv, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    out = build_wheel(str(dist))
    (wheel,) = dist.glob("dynamic-0.0.2-*.whl")
    wheel = wheel.resolve()  # Windows mingw64 and UCRT now requires this
    assert wheel == dist / out

    virtualenv.install(wheel)
    license = virtualenv.execute(
        "from importlib.metadata import metadata; print(metadata('dynamic')['License'])"
    )
    assert license == "MIT License"

    with zipfile.ZipFile(wheel) as zf:
        file_paths = {Path(n) for n in zf.namelist()}

    dynamic_pkg = {x.name for x in contained(file_paths, "dynamic")}
    filtered_pkg = {x for x in dynamic_pkg if not x.startswith("_module")}

    assert len(filtered_pkg) == len(dynamic_pkg) - 1
    assert {"dynamic-0.0.2.dist-info", "dynamic"} == {p.parts[0] for p in file_paths}
    assert {"__init__.py"} == filtered_pkg

    version = virtualenv.execute("from dynamic import square; print(square(2))")
    assert version == "4.0"


def test_regex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = tmp_path / "test_regex"
    d.mkdir()
    monkeypatch.chdir(d)

    with Path("__init__.py").open("w") as f:
        f.write("__version__ = '0.1.0'")

    regex.dynamic_metadata("version", {"input": "__init__.py"})


def test_regex_errors() -> None:
    with pytest.raises(RuntimeError):
        regex.dynamic_metadata("version", {})


def test_multipart_regex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = tmp_path / "test_multi_regex"
    d.mkdir()
    monkeypatch.chdir(d)

    with Path("version.hpp").open("w") as f:
        f.write(
            textwrap.dedent(
                """\
            #define VERSION_MAJOR 1
            // Comment
            #define VERSION_MINOR 2
            #define VERSION_PATCH 3dev1
            """
            )
        )

    version = regex.dynamic_metadata(
        "version",
        {
            "input": "version.hpp",
            "regex": r"""(?sx)
            \#define \s+ VERSION_MAJOR \s+ (?P<major>\d+) .*?
            \#define \s+ VERSION_MINOR \s+ (?P<minor>\d+) .*?
            \#define \s+ VERSION_PATCH \s+ (?P<patch>\w+)
            """,
            "result": "{major}.{minor}.{patch}",
        },
    )

    assert version == "1.2.3dev1"


@pytest.mark.parametrize("dev", [0, 1])
def test_regex_remove(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dev: int
) -> None:
    d = tmp_path / "test_multidev_regex"
    d.mkdir()
    monkeypatch.chdir(d)

    with Path("version.hpp").open("w") as f:
        f.write(
            textwrap.dedent(
                f"""\
                #define VERSION_MAJOR 1
                // Comment
                #define VERSION_MINOR 2
                #define VERSION_PATCH 3
                #define VERSION_DEV {dev}
                """
            )
        )

    version = regex.dynamic_metadata(
        "version",
        {
            "input": "version.hpp",
            "regex": r"""(?sx)
            \#define \s+ VERSION_MAJOR \s+ (?P<major>\d+) .*?
            \#define \s+ VERSION_MINOR \s+ (?P<minor>\d+) .*?
            \#define \s+ VERSION_PATCH \s+ (?P<patch>\d+) .*?
            \#define \s+ VERSION_DEV \s+ (?P<dev>\d+)
            """,
            "result": "{major}.{minor}.{patch}dev{dev}",
            "remove": r"dev0",
        },
    )

    assert version == ("1.2.3dev1" if dev else "1.2.3")


def test_array_dynamic_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end check of the standard top-level [[tool.dynamic-metadata]]."""
    d = tmp_path / "test_array"
    d.mkdir()
    monkeypatch.chdir(d)

    Path("version.txt").write_text("VERSION = '1.2.3'\n", encoding="utf-8")
    Path("local_plugins").mkdir()
    Path("local_plugins/req_plugin.py").write_text(
        "def dynamic_metadata(settings, project):\n"
        "    return {'requires-python': '>=' + project['version']}\n"
        "def get_requires_for_dynamic_metadata(settings):\n"
        "    return ['extra-build-dep']\n",
        encoding="utf-8",
    )
    Path("pyproject.toml").write_text(
        textwrap.dedent(
            """\
            [build-system]
            requires = ["scikit-build-core"]
            build-backend = "scikit_build_core.build"

            [project]
            name = "test-array"
            dynamic = ["version", "requires-python"]

            [[tool.dynamic-metadata]]
            provider = "scikit_build_core.metadata.regex"
            field = "version"
            input = "version.txt"

            [[tool.dynamic-metadata]]
            provider = "req_plugin"
            provider-path = "local_plugins"
            """
        ),
        encoding="utf-8",
    )

    with Path("pyproject.toml").open("rb") as ft:
        pyproject = tomllib.load(ft)
    settings = SettingsReader(pyproject, {}, state="metadata_wheel").settings

    metadata = get_standard_metadata(pyproject, settings, build_state="sdist")
    assert str(metadata.version) == "1.2.3"
    assert str(metadata.requires_python) == ">=1.2.3"

    assert "extra-build-dep" in set(GetRequires().dynamic_metadata())


def test_regex_both_forms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The bundled regex plugin gives the same result in both config forms."""
    from scikit_build_core.builder._load_provider import (
        process_dynamic_metadata,
        process_legacy_dynamic_metadata,
    )

    monkeypatch.chdir(tmp_path)
    Path("__init__.py").write_text("__version__ = '0.1.0'\n", encoding="utf-8")

    def project() -> dict[str, Any]:
        return {"name": "p", "dynamic": ["version"]}

    legacy = process_legacy_dynamic_metadata(
        project(),
        {
            "version": {
                "provider": "scikit_build_core.metadata.regex",
                "input": "__init__.py",
            }
        },
    )
    array = process_dynamic_metadata(
        project(),
        [
            {
                "provider": "scikit_build_core.metadata.regex",
                "field": "version",
                "input": "__init__.py",
            }
        ],
    )
    assert legacy["version"] == array["version"] == "0.1.0"


def test_template_both_forms() -> None:
    """The bundled template plugin gives the same result in both config forms."""
    from scikit_build_core.builder._load_provider import (
        process_dynamic_metadata,
        process_legacy_dynamic_metadata,
    )

    result = {"dev": ["{project[name]}=={project[version]}"]}

    def project() -> dict[str, Any]:
        return {"name": "pkg", "version": "1.0", "dynamic": ["optional-dependencies"]}

    legacy = process_legacy_dynamic_metadata(
        project(),
        {
            "optional-dependencies": {
                "provider": "scikit_build_core.metadata.template",
                "result": result,
            }
        },
    )
    array = process_dynamic_metadata(
        project(),
        [
            {
                "provider": "scikit_build_core.metadata.template",
                "field": "optional-dependencies",
                "result": result,
            }
        ],
    )
    assert legacy["optional-dependencies"] == array["optional-dependencies"]
    assert array["optional-dependencies"] == {"dev": ["pkg==1.0"]}


def test_legacy_does_not_mutate_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The legacy table must not mutate the caller's project dict."""
    from scikit_build_core.builder._load_provider import process_legacy_dynamic_metadata

    monkeypatch.chdir(tmp_path)
    Path("__init__.py").write_text("__version__ = '0.1.0'\n", encoding="utf-8")

    project = {"name": "p", "dynamic": ["version"]}
    process_legacy_dynamic_metadata(
        project,
        {
            "version": {
                "provider": "scikit_build_core.metadata.regex",
                "input": "__init__.py",
            }
        },
    )
    assert project == {"name": "p", "dynamic": ["version"]}


def test_array_legacy_plugin_requires_field() -> None:
    """A bundled (legacy-signature) plugin in the array form needs a 'field'."""
    from scikit_build_core.builder._load_provider import process_dynamic_metadata

    with pytest.raises(RuntimeError, match="field"):
        process_dynamic_metadata(
            {"name": "p", "dynamic": ["version"]},
            [{"provider": "scikit_build_core.metadata.regex", "input": "x"}],
        )


def test_mixing_metadata_forms_rejected() -> None:
    pyproject = {
        "project": {"name": "t", "dynamic": ["version"]},
        "tool": {
            "scikit-build": {
                "metadata": {
                    "version": {"provider": "scikit_build_core.metadata.setuptools_scm"}
                }
            },
            "dynamic-metadata": [
                {
                    "provider": "scikit_build_core.metadata.regex",
                    "field": "version",
                    "input": "x",
                }
            ],
        },
    }
    reader = SettingsReader(pyproject, {}, state="metadata_wheel")
    with pytest.raises(SystemExit):
        reader.validate_may_exit()


@pytest.mark.parametrize("override", [None, "env", "sdist"])
@pytest.mark.parametrize("package", ["dynamic_metadata"], indirect=True)
@pytest.mark.usefixtures("package")
def test_build_requires_field(override, monkeypatch) -> None:
    shutil.copy("build_requires_project.toml", "pyproject.toml")

    if override == "env":
        monkeypatch.setenv("LOCAL_FOO", "True")
    else:
        monkeypatch.delenv("LOCAL_FOO", raising=False)

    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as ft:
        pyproject = tomllib.load(ft)
    state: Literal["sdist", "metadata_wheel"] = (
        "sdist" if override == "sdist" else "metadata_wheel"
    )
    settings_reader = SettingsReader(pyproject, {}, state=state)

    settings_reader.validate_may_exit()

    if override is None:
        assert set(GetRequires().dynamic_metadata()) == {
            "foo",
        }
    elif override == "env":
        # evaluate ../foo as uri
        foo_path = pyproject_path.absolute().parent.parent / "foo"
        foo_path = foo_path.absolute()
        assert set(GetRequires().dynamic_metadata()) == {
            f"foo @ {foo_path.as_uri()}",
        }
    elif override == "sdist":
        assert set(GetRequires().dynamic_metadata()) == {
            # TODO: Check if special handling should be done for sdist
            "foo",
        }
