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
    assert "fail = false" in docs
    # Deprecated items are not included here
    assert "ninja.minimum-version" not in docs


def test_skbuild_docs_sphinx() -> None:
    docs = mk_skbuild_docs_sphinx()
    assert (
        textwrap.dedent("""\
    .. confval:: cmake.define
      :type: ``EnvVar``
    
      A table of defines to pass to CMake when configuring the project. Additive.
    """)
        in docs
    )
    assert (
        textwrap.dedent("""\
    .. confval:: ninja.minimum-version
      :type: ``Version``

      DEPRECATED in 0.8; use version instead.
    """)
        in docs
    )


def test_mk_docs() -> None:
    docs = set(mk_docs(ScikitBuildSettings))

    dcdoc = next(item for item in docs if item.name == "cmake.define")
    assert dcdoc.type == "EnvVar"
    assert dcdoc.default == "{}"
    assert (
        dcdoc.docs
        == "A table of defines to pass to CMake when configuring the project. Additive."
    )
    assert dcdoc.deprecated is False
