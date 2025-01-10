from __future__ import annotations

__all__ = ["generate_file_contents"]

import dataclasses
import string
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._vendor.pyproject_metadata import StandardMetadata
    from ..settings.skbuild_model import GenerateSettings


def __dir__() -> list[str]:
    return __all__


def generate_file_contents(gen: GenerateSettings, metadata: StandardMetadata) -> str:
    """
    Generate a file contents from a template. Input GeneratorSettings and
    metadata. Metadata is available inside the template.
    """

    assert gen.template_path or gen.template, (
        f"One of template or template-path must be set for {gen.path}"
    )

    if gen.template_path:
        template = gen.template_path.read_text(encoding="utf-8")
    else:
        template = gen.template

    return string.Template(template).substitute(dataclasses.asdict(metadata))
