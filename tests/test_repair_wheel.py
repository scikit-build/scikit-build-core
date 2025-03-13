import platform
import shutil
from pathlib import Path

import pytest

DIR = Path(__file__).parent.resolve()
REPAIR_WHEEL = DIR / "packages/repair_wheel"


@pytest.mark.compile
@pytest.mark.configure
@pytest.mark.parametrize(
    ("backend", "with_isolation", "manual_repair"),
    [
        ("pip", True, False),
        ("pip", False, False),
        ("pip", True, True),
        ("build", True, False),
        ("build", False, False),
    ],
    ids=[
        "pip-isolated",
        "pip-not-isolated",
        "manual",
        "build-isolated",
        "build-not-isolated",
    ],
)
@pytest.mark.usefixtures("repair_wheel")
def test_full_build(
    backend,
    isolated,
    with_isolation,
    manual_repair,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("MANUAL", f"{manual_repair}")
    if backend == "pip":
        isolated.install("pip>=23")
    elif backend == "build":
        isolated.install("build[virtualenv]")
    else:
        raise NotImplementedError

    if not with_isolation:
        isolated.install("scikit-build-core")
        if platform.system() == "Linux":
            isolated.install("auditwheel")
            if shutil.which("patchelf") is None:
                isolated.install("patchelf")
        if platform.system() == "Darwin":
            isolated.install("delocate")
        isolated.install("./extern", isolated=with_isolation)

    if backend == "pip":
        isolated.install(
            "-v",
            "./extern",
            ".",
            isolated=with_isolation,
        )
    elif backend == "build":
        dist = tmp_path / "dist"
        build_args = ["-v", "--wheel", f"--outdir={dist}"]
        if with_isolation:
            isolated.module("build", *build_args, "./extern")
        else:
            build_args.append("--no-isolation")
        isolated.module("build", *build_args, ".")
        wheels = list(dist.glob("*.whl"))
        isolated.install(*wheels)

    if platform.system() != "Windows":
        # Requires a more specialized patch
        isolated.run("main")
        isolated.module("repair_wheel")
    isolated.execute(
        "from repair_wheel._module import hello; hello()",
    )
