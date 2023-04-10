from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

from scikit_build_core.build import (
    prepare_metadata_for_build_editable,
    prepare_metadata_for_build_wheel,
)


@pytest.mark.usefixtures("package_simplest_c")
@pytest.mark.parametrize("editable", [True, False], ids=["editable", "wheel"])
def test_prepare_metadata_for_build(fp, editable):
    # Old versions of packaging call mac_ver via subprocess
    fp.pass_command([sys.executable, fp.any()])
    fp.pass_command([fp.program("cmake"), "--version"])
    fp.pass_command([fp.program("cmake3"), "--version"])

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
        Metadata-Version: 2.1
        Name: simplest
        Version: 0.0.1"""
        )
        == metadata.strip()
    )

    assert len(list(Path("simple/simplest-0.0.1.dist-info").iterdir())) == 3
    assert len(list(Path("simple").iterdir())) == 1
