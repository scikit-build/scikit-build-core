import pytest


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
@pytest.mark.parametrize("isolate", [True, False])
@pytest.mark.usefixtures("navigate_editable")
def test_navigate_editable(isolated, isolate):
    isolate_args = ["--no-build-isolation"] if not isolate else []
    isolated.install("pip>=23")
    if not isolate:
        isolated.install("scikit-build-core[pyproject]")

    isolated.install(
        "-v", "--config-settings=build-dir=build/{wheel_tag}", *isolate_args, "-e", "."
    )

    value = isolated.execute("import shared_pkg; shared_pkg.call_c_method()")
    assert value == "c_method"

    value = isolated.execute("import shared_pkg; shared_pkg.call_py_method()")
    assert value == "py_method"

    value = isolated.execute("import shared_pkg; shared_pkg.read_py_data_txt()")
    assert value == "Some_value_Py"

    value = isolated.execute("import shared_pkg; shared_pkg.read_c_generated_txt()")
    assert value == "Some_value_C"
