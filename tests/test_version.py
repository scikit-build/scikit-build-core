from __future__ import annotations

import scikit_build_core


def test_version():
    assert isinstance(scikit_build_core.__version__, str)
    assert len(scikit_build_core.__version__) > 0


def test_all():
    assert scikit_build_core.__all__ == ["__version__"]
