import pytest
from packaging.version import Version

from scikit_build_core.settings.auto_requires import get_min_requires


def test_auto_requires_pkg_no_spec():
    reqlist = ["scikit-build-core"]

    assert get_min_requires("scikit-build-core", reqlist) is None
    assert get_min_requires("other", reqlist) is None


@pytest.mark.parametrize(
    ("spec", "version"),
    [
        ("==1.0", Version("1.0")),
        (">=1.0", Version("1.0")),
        (">1.0", Version("1.0")),
        ("~=1.0", Version("1.0")),
        (">=0.3,<0.4", Version("0.3")),
        ("", None),
    ],
)
def test_auto_requires_pkg_version(spec: str, version: Version):
    reqlist = [f"scikit_build_core{spec}"]
    assert get_min_requires("scikit-build-core", reqlist) == version
