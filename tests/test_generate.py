from __future__ import annotations

import dataclasses
from pathlib import Path  # noqa: TC003

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
    gen = type(
        "Gen",
        (),
        {
            "template": "name=$name, version=$version",
            "template_path": None,
            "path": "out.txt",
        },
    )
    assert generate_file_contents(gen, fake_metadata) == "name=test_pkg, version=1.2.3"


def test_generate_from_template_path(tmp_path: Path, fake_metadata) -> None:
    template_file = tmp_path / "template.txt"
    template_file.write_text("version=$version")

    gen = type(
        "Gen",
        (),
        {
            "template": None,
            "template_path": template_file,
            "path": "out.txt",
        },
    )
    assert generate_file_contents(gen, fake_metadata) == "version=1.2.3"


def test_generate_missing_template(fake_metadata) -> None:
    gen = type(
        "Gen",
        (),
        {
            "template": None,
            "template_path": None,
            "path": "out.txt",
        },
    )
    with pytest.raises(AssertionError):
        generate_file_contents(gen, fake_metadata)
