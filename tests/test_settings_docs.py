from __future__ import annotations

from scikit_build_core.settings.documentation import DCDoc, mk_docs
from scikit_build_core.settings.skbuild_docs import mk_skbuild_docs
from scikit_build_core.settings.skbuild_model import ScikitBuildSettings


def test_skbuild_docs() -> None:
    docs = mk_skbuild_docs()
    assert (
        "A table of defines to pass to CMake when configuring the project. Additive."
        in docs
    )
    assert "DEPRECATED in 0.10, use build.verbose instead." in docs
    assert "fail = false" in docs


def test_mk_docs() -> None:
    docs = set(mk_docs(ScikitBuildSettings))

    assert (
        DCDoc(
            name="cmake.minimum-version",
            default='""',
            docs="DEPRECATED in 0.8; use version instead.",
            deprecated=True,
        )
        in docs
    )
    assert (
        DCDoc(
            name="install.strip",
            default="true",
            docs="Whether to strip the binaries. True for release builds on scikit-build-core 0.5+ (0.5-0.10.5 also incorrectly set this for debug builds).",
            deprecated=False,
        )
        in docs
    )
