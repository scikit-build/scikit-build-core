import zipfile
from pathlib import Path

import pytest

from scikit_build_core.build import build_wheel

SPDX_CONTENT = '{"spdxVersion": "SPDX-2.3", "SPDXID": "SPDXRef-DOCUMENT"}'
CYCLONEDX_CONTENT = '{"bomFormat": "CycloneDX", "specVersion": "1.5"}'


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("project.spdx.json", SPDX_CONTENT),
        ("bom.json", CYCLONEDX_CONTENT),
    ],
    ids=["spdx", "cyclonedx"],
)
@pytest.mark.parametrize("package", ["simple_purelib_package"], indirect=True)
@pytest.mark.usefixtures("package")
def test_pep770_wheel_sbom_files(tmp_path: Path, filename: str, content: str):
    sbom_dir = Path("sbom_inputs")
    sbom_dir.mkdir()
    sbom_file = sbom_dir / filename
    sbom_file.write_text(content, encoding="utf-8")

    dist = tmp_path / "dist"
    build_wheel(str(dist), {"wheel.sbom-files": [str(sbom_file)]})

    (wheel,) = dist.glob("purelib_example-0.0.1-*.whl")
    wheel = wheel.resolve()
    with zipfile.ZipFile(wheel) as zf:
        sbom_path = f"purelib_example-0.0.1.dist-info/sboms/{filename}"
        assert sbom_path in set(zf.namelist())
        assert zf.read(sbom_path).decode("utf-8") == content


@pytest.mark.parametrize("package", ["simple_purelib_package"], indirect=True)
@pytest.mark.usefixtures("package")
def test_pep770_wheel_sbom_file_missing(tmp_path: Path):
    dist = tmp_path / "dist"
    with pytest.raises(
        FileNotFoundError, match=r"SBOM file not found: missing_sbom\.json"
    ):
        build_wheel(str(dist), {"wheel.sbom-files": ["missing_sbom.json"]})
