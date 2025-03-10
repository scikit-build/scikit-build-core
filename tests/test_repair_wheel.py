import platform
import shutil
from pathlib import Path

import pytest

DIR = Path(__file__).parent.resolve()
REPAIR_WHEEL = DIR / "packages/repair_wheel"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize(
    ("isolate", "manual_repair"),
    [
        (True, False),
        (False, False),
        (True, True),
    ],
    ids=["isolated", "notisolated", "manual"],
)
@pytest.mark.usefixtures("repair_wheel")
def test_full_build(isolated, isolate, manual_repair, monkeypatch):
    monkeypatch.setenv("MANUAL", f"{manual_repair}")
    isolated.install("pip>=23")
    if not isolate:
        isolated.install("scikit-build-core")
        if platform.system() == "Linux":
            isolated.install("auditwheel")
            if shutil.which("patchelf") is None:
                isolated.install("patchelf")
        if platform.system() == "Darwin":
            isolated.install("delocate")
        if platform.system() == "Windows":
            isolated.install("delvewheel")
        isolated.install("./extern", isolated=isolate)

    isolated.install(
        "-v", "--config-settings=logging.level=DEBUG", "./extern", ".", isolated=isolate
    )

    # isolated.run("main")
    # isolated.module("repair_wheel")
    isolated.execute(
        "from repair_wheel._module import hello; hello()",
    )
