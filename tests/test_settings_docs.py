from __future__ import annotations

import dataclasses
import textwrap
from typing import Annotated, Any, get_args, get_origin

from scikit_build_core.settings.documentation import mk_docs
from scikit_build_core.settings.skbuild_docs_readme import (
    mk_skbuild_docs as mk_skbuild_docs_readme,
)
from scikit_build_core.settings.skbuild_docs_sphinx import (
    mk_skbuild_docs as mk_skbuild_docs_sphinx,
)
from scikit_build_core.settings.skbuild_model import FieldScope, ScikitBuildSettings
from scikit_build_core.utils.typing import is_union_type


def test_skbuild_docs_readme() -> None:
    docs = mk_skbuild_docs_readme()
    assert docs.startswith("### Top-level")
    assert "### `cmake`" in docs
    assert (
        "| `cmake.define` | `{}` | A table of defines to pass to CMake when configuring the project. Additive. |"
        in docs
    )
    assert "`fail`" not in docs
    # Deprecated items are not included here
    assert "DEPRECATED" not in docs


def test_skbuild_docs_sphinx() -> None:
    docs = mk_skbuild_docs_sphinx()
    assert (
        textwrap.dedent("""\
    .. confval:: cmake.define

      :Type: ``dict[str,CMakeSettingsDefine]``
      :Config-settings: ``cmake.define`` or ``skbuild.cmake.define``
      :Environment variable: ``SKBUILD_CMAKE_DEFINE``

      A table of defines to pass to CMake when configuring the project. Additive.
    """)
        in docs
    )
    assert (
        textwrap.dedent("""\
    .. confval:: ninja.minimum-version

      :Type: ``Version``
      :Config-settings: ``ninja.minimum-version`` or ``skbuild.ninja.minimum-version``
      :Environment variable: ``SKBUILD_NINJA_MINIMUM_VERSION``

      DEPRECATED in 0.8; use version instead.
    """)
        in docs
    )
    # Arrays of tables can't be set via the environment, so no flat forms shown.
    assert (
        textwrap.dedent("""\
    .. confval:: generate[].path

      :Type: ``Path``

      The path (relative to platlib) for the file to generate.
    """)
        in docs
    )
    # Nested mappings (dict of dict) can't be expressed as a flat key either.
    assert (
        textwrap.dedent("""\
    .. confval:: metadata

      :Type: ``dict[str,dict[str,Any]]``

      List dynamic metadata fields and hook locations in this table.
    """)
        in docs
    )


def test_mk_docs() -> None:
    docs = set(mk_docs(ScikitBuildSettings))

    dcdoc = next(item for item in docs if item.name == "cmake.define")
    assert dcdoc.type == "dict[str,CMakeSettingsDefine]"
    assert dcdoc.default == "{}"
    assert (
        dcdoc.docs
        == "A table of defines to pass to CMake when configuring the project. Additive."
    )
    assert dcdoc.deprecated is False


def _flat_expressible(field_type: Any) -> bool:
    """Whether -C and SKBUILD_* env vars can express a value of this type."""
    origin = get_origin(field_type)
    if origin is Annotated:
        return _flat_expressible(get_args(field_type)[0])
    if is_union_type(origin):
        return all(_flat_expressible(arg) for arg in get_args(field_type))
    if origin is dict:
        return get_origin(get_args(field_type)[1]) not in (dict, list)
    if origin is list:
        (item,) = get_args(field_type)
        return not dataclasses.is_dataclass(item)
    return True


def _non_flat_fields(dc: type[Any], prefix: str = "") -> list[str]:
    names = []
    for field in dataclasses.fields(dc):
        name = f"{prefix}{field.name}".replace("_", "-")
        if dataclasses.is_dataclass(field.type):
            names += _non_flat_fields(field.type, f"{name}.")  # type: ignore[arg-type]
        elif not _flat_expressible(field.type):
            names.append(name)
    return names


def test_non_flat_fields_are_static() -> None:
    """Flat sources cannot set these, so the docs must not advertise them."""
    scopes = {item.name: item.scope for item in mk_docs(ScikitBuildSettings)}
    non_flat = _non_flat_fields(ScikitBuildSettings)
    assert "metadata" in non_flat
    assert "generate" in non_flat
    for name in non_flat:
        if name in scopes:
            assert scopes[name] is FieldScope.STATIC, name
        else:
            children = [k for k in scopes if k.startswith(f"{name}[].")]
            assert children, name
            assert all(scopes[k] is FieldScope.STATIC for k in children), name
