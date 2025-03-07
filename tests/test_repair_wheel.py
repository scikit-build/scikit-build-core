from pathlib import Path

import pytest

DIR = Path(__file__).parent.resolve()
REPAIR_WHEEL = DIR / "packages/repair_wheel"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize("isolate", [True, False], ids=["isolated", "notisolated"])
@pytest.mark.usefixtures("repair_wheel")
def test_full_build(isolated, isolate):
    isolate_args = ["--no-build-isolation"] if not isolate else []
    isolated.install("pip>=23")
    if not isolate:
        isolated.install("scikit-build-core[repair-wheel]")
        isolated.install("-v", *isolate_args, "./extern")

    isolated.install("-v", *isolate_args, ".")

    isolated.run("main")
    isolated.module("repair_wheel")
    isolated.execute(
        "from repair_wheel._module import hello; hello()",
    )
