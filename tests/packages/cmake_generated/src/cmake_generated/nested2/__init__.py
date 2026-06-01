from importlib.resources import files


def nested1_generated_check():
    # noinspection PyUnresolvedReferences
    from ..nested1.generated import nested_data  # type: ignore[import-not-found]

    return nested_data


def get_generated_data():
    # Build-tree-generated data living in this regular subpackage, which has no
    # generated Python module of its own.  The file name is not a valid module
    # name, so it is only reachable if the build-tree path is propagated here.
    return (
        files("cmake_generated.nested2")
        .joinpath("nested2-generated-data.txt")
        .read_text()
        .rstrip()
    )
