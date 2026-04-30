from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from scikit_build_core.build.generate import generate_file_contents


@pytest.fixture
def fake_metadata():
    @dataclasses.dataclass
    class FakeMetadata:
        name: str = "test_pkg"
        version: str = "1.2.3"

    return FakeMetadata()


def test_generate_from_template(fake_metadata) -> None:
    class Gen:
        template = "name=$name, version=$version"
        template_path = None
        path = Path("out.txt")

    assert (
        generate_file_contents(Gen(), fake_metadata)  # type: ignore[arg-type]
        == "name=test_pkg, version=1.2.3"
    )


def test_generate_from_template_path(tmp_path: Path, fake_metadata) -> None:
    template_file = tmp_path / "template.txt"
    template_file.write_text("version=$version")

    class Gen:
        template = None
        template_path = template_file
        path = Path("out.txt")

    assert (
        generate_file_contents(Gen(), fake_metadata)  # type: ignore[arg-type]
        == "version=1.2.3"
    )


def test_generate_missing_template(fake_metadata) -> None:
    class Gen:
        template = None
        template_path = None
        path = Path("out.txt")

    with pytest.raises(AssertionError):
        generate_file_contents(Gen(), fake_metadata)  # type: ignore[arg-type]
