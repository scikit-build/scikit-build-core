from __future__ import annotations

import sys
import textwrap
import types
from pathlib import Path
from typing import Any

import pytest
from packaging.version import Version

from scikit_build_core.build import (
    prepare_metadata_for_build_editable,
    prepare_metadata_for_build_wheel,
)
from scikit_build_core.build.metadata import get_standard_metadata
from scikit_build_core.settings.skbuild_model import ScikitBuildSettings


@pytest.mark.parametrize("package", ["simplest_c"], indirect=True)
@pytest.mark.usefixtures("package")
@pytest.mark.parametrize("editable", [True, False], ids=["editable", "wheel"])
def test_prepare_metadata_for_build(fp, editable):
    # Old versions of packaging call mac_ver via subprocess
    fp.pass_command([sys.executable, fp.any()])
    fp.pass_command([fp.program("cmake"), "-E", "capabilities"])
    fp.pass_command([fp.program("cmake3"), "-E", "capabilities"])
    fp.register(
        ["lipo", "-info", fp.program("cmake")],
        stdout="Architectures in the fat file: ... are: x86_64 arm64",
    )
    fp.register(
        ["lipo", "-info", fp.program("cmake3")],
        stdout="Architectures in the fat file: ... are: x86_64 arm64",
    )

    if editable:
        assert (
            prepare_metadata_for_build_editable("simple") == "simplest-0.0.1.dist-info"
        )
    else:
        assert prepare_metadata_for_build_wheel("simple") == "simplest-0.0.1.dist-info"

    with Path("simple/simplest-0.0.1.dist-info").joinpath("METADATA").open() as f:
        metadata = f.read()
    assert (
        textwrap.dedent(
            """\
        Metadata-Version: 2.2
        Name: simplest
        Version: 0.0.1"""
        )
        == metadata.strip()
    )

    assert len(list(Path("simple/simplest-0.0.1.dist-info").iterdir())) == 2
    assert len(list(Path("simple").iterdir())) == 1


def test_multiline_description():
    with pytest.raises(ValueError, match="one line summary"):
        get_standard_metadata(
            pyproject_dict={
                "project": {
                    "name": "hello",
                    "version": "1.1.1",
                    "description": "One\nTwo",
                }
            },
            settings=ScikitBuildSettings(),
        )

    with pytest.raises(ValueError, match="one line summary"):
        get_standard_metadata(
            pyproject_dict={
                "project": {
                    "name": "hello",
                    "version": "1.1.1",
                    "description": "One\nTwo",
                }
            },
            settings=ScikitBuildSettings(minimum_version=Version("0.9")),
        )

    get_standard_metadata(
        pyproject_dict={
            "project": {"name": "hello", "version": "1.1.1", "description": "One\nTwo"}
        },
        settings=ScikitBuildSettings(minimum_version=Version("0.8")),
    )


def test_license_normalization():
    pytest.importorskip("packaging.licenses")
    metadata = get_standard_metadata(
        pyproject_dict={
            "project": {"name": "hello", "version": "1.1.1", "license": "ApacHE-2.0"}
        },
        settings=ScikitBuildSettings(),
    )
    assert metadata.license == "Apache-2.0"


@pytest.mark.usefixtures("package_simple_pyproject_ext")
def test_prepare_metadata_for_build_wheel_variant(fp, monkeypatch, tmp_path):
    fp.pass_command([sys.executable, fp.any()])
    fp.pass_command([fp.program("cmake"), "-E", "capabilities"])
    fp.pass_command([fp.program("cmake3"), "-E", "capabilities"])
    fp.register(
        ["lipo", "-info", fp.program("cmake")],
        stdout="Architectures in the fat file: ... are: x86_64 arm64",
    )
    fp.register(
        ["lipo", "-info", fp.program("cmake3")],
        stdout="Architectures in the fat file: ... are: x86_64 arm64",
    )

    variantlib: Any = types.ModuleType("variantlib")
    variantlib_api: Any = types.ModuleType("variantlib.api")
    variantlib_errors: Any = types.ModuleType("variantlib.errors")
    variantlib_models: Any = types.ModuleType("variantlib.models")
    variantlib_models_variant: Any = types.ModuleType("variantlib.models.variant")
    variantlib_pyproject: Any = types.ModuleType("variantlib.pyproject_toml")

    class ValidationError(Exception):
        pass

    class VariantProperty:
        def __init__(self, raw: str) -> None:
            self.raw = raw

        @classmethod
        def from_str(cls, raw: str):
            return cls(raw)

    class VariantDescription:
        def __init__(self, properties) -> None:
            self.properties = properties

    class VariantPyProjectToml:
        def __init__(self, pyproject) -> None:
            self.pyproject = pyproject

    def get_variant_label(variant, label):
        _ = variant
        return label or "cpu"

    def make_variant_dist_info(variant, *, variant_info, variant_label):
        _ = variant_info
        raw = ",".join(prop.raw for prop in variant.properties)
        return f"label={variant_label or 'cpu'};properties={raw}"

    variantlib_api.get_variant_label = get_variant_label
    variantlib_api.make_variant_dist_info = make_variant_dist_info
    variantlib_errors.ValidationError = ValidationError
    variantlib_models_variant.VariantDescription = VariantDescription
    variantlib_models_variant.VariantProperty = VariantProperty
    variantlib_pyproject.VariantPyProjectToml = VariantPyProjectToml

    monkeypatch.setitem(sys.modules, "variantlib", variantlib)
    monkeypatch.setitem(sys.modules, "variantlib.api", variantlib_api)
    monkeypatch.setitem(sys.modules, "variantlib.errors", variantlib_errors)
    monkeypatch.setitem(sys.modules, "variantlib.models", variantlib_models)
    monkeypatch.setitem(
        sys.modules, "variantlib.models.variant", variantlib_models_variant
    )
    monkeypatch.setitem(sys.modules, "variantlib.pyproject_toml", variantlib_pyproject)

    mddir = tmp_path / "dist"
    mddir.mkdir()
    out = prepare_metadata_for_build_wheel(
        str(mddir),
        {
            "experimental": "true",
            "variant": "cpu :: abi :: cp313",
            "variant-label": "cpu",
        },
    )

    assert out == "cmake_example-0.0.1.dist-info"
    assert (
        mddir / out / "variant.json"
    ).read_text() == "label=cpu;properties=cpu :: abi :: cp313"
