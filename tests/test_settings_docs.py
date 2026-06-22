from __future__ import annotations

import textwrap

from scikit_build_core.settings.documentation import mk_docs
from scikit_build_core.settings.skbuild_docs_readme import (
    mk_skbuild_docs as mk_skbuild_docs_readme,
)
from scikit_build_core.settings.skbuild_docs_sphinx import (
    mk_skbuild_docs as mk_skbuild_docs_sphinx,
)
from scikit_build_core.settings.skbuild_model import ScikitBuildSettings


def test_skbuild_docs_readme() -> None:
    docs = mk_skbuild_docs_readme()
    assert (
        "A table of defines to pass to CMake when configuring the project. Additive."
        in docs
    )
    assert "fail = " not in docs
    # Deprecated items are not included here
    assert "ninja.minimum-version" not in docs


def test_skbuild_docs_sphinx() -> None:
    docs = mk_skbuild_docs_sphinx()
    assert (
        textwrap.dedent("""\
    .. confval:: cmake.define
      :type: ``dict[str,CMakeSettingsDefine]``
      :env: ``SKBUILD_CMAKE_DEFINE``

      A table of defines to pass to CMake when configuring the project. Additive.
    """)
        in docs
    )
    assert (
        textwrap.dedent("""\
    .. confval:: ninja.minimum-version
      :type: ``Version``
      :env: ``SKBUILD_NINJA_MINIMUM_VERSION``

      DEPRECATED in 0.8; use version instead.
    """)
        in docs
    )
    # Arrays of tables can't be set via the environment, so no :env: is shown.
    assert (
        textwrap.dedent("""\
    .. confval:: generate[].path
      :type: ``Path``

      The path (relative to platlib) for the file to generate.
    """)
        in docs
    )
    # Nested mappings (dict of dict) can't be expressed as an env var either.
    assert (
        textwrap.dedent("""\
    .. confval:: metadata
      :type: ``dict[str,dict[str,Any]]``

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
