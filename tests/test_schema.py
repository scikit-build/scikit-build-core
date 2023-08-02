from scikit_build_core.settings.skbuild_schema import (
    generate_skbuild_schema,
    get_skbuild_schema,
)


def test_compare_schemas():
    """
    Should be the same. If not, run nox -s generate_schema
    """

    assert generate_skbuild_schema() == get_skbuild_schema()
