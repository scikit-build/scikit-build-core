import sys
from pathlib import Path

import pytest


@pytest.mark.compile()
@pytest.mark.configure()
@pytest.mark.integration()
@pytest.mark.parametrize("isolate", [True, False], ids=["isolated", "notisolated"])
@pytest.mark.parametrize(
    "package",
    [
        pytest.param(
            True,
            id="package",
            marks=[pytest.mark.xfail(reason="Only data folders supported currently")],
        ),
        pytest.param(False, id="datafolder"),
    ],
)
@pytest.mark.usefixtures("navigate_editable")
@pytest.mark.xfail(
    sys.version_info[:2] == (3, 9), reason="Python 3.9 not supported yet"
)
def test_navigate_editable(isolated, isolate, package):
    isolate_args = ["--no-build-isolation"] if not isolate else []
    isolated.install("pip>=23")
    if not isolate:
        isolated.install("scikit-build-core[pyproject]")

    if package:
        init_py = Path("python/shared_pkg/data/__init__.py")
        init_py.touch()

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
