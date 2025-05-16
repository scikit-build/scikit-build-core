# Projects

There are over 600 projects using scikit-build-core on PyPI (as of May 2025).
This is a selection of some of the projects. Feel free to add your own project
to `docs/data/projects.toml`. The following selection was primarily constructed
by looking at the [top 15,000](https://hugovk.github.io/top-pypi-packages/) most
downloaded projects on PyPI for top-level pyproject.toml's in SDists that use
scikit-build-core.

<!-- prettier-ignore-start -->

<!--[[[cog
import cog
import collections
import tomllib
from pathlib import Path

DIR = Path(cog.inFile).parent
PROJECTS = DIR.parent / "data/projects.toml"

with PROJECTS.open("rb") as f:
    projects = tomllib.load(f)

project_names = [p["pypi"].lower() for p in projects["project"]]
counts = collections.Counter(project_names)
dups = {k:v for k, v in counts.items() if v > 1}
if dups:
    msg = f"Duplicate projects: {dups}"
    raise AssertionError(msg)

for project in projects["project"]:
    pypi = project["pypi"]
    github = project["github"]
    path = project.get("path", "pyproject.toml")

    cog.outl(f"* [{pypi}](https://pypi.org/project/{pypi}) ([source](https://github.com/{github}/blob/HEAD/{path}))")
]]]-->
* [cmake](https://pypi.org/project/cmake) ([source](https://github.com/scikit-build/cmake-python-distributions/blob/HEAD/pyproject.toml))
* [ninja](https://pypi.org/project/ninja) ([source](https://github.com/scikit-build/ninja-python-distributions/blob/HEAD/pyproject.toml))
* [pyzmq](https://pypi.org/project/pyzmq) ([source](https://github.com/zeromq/pyzmq/blob/HEAD/pyproject.toml))
* [lightgbm](https://pypi.org/project/lightgbm) ([source](https://github.com/microsoft/LightGBM/blob/HEAD/python-package/pyproject.toml))
* [phik](https://pypi.org/project/phik) ([source](https://github.com/kaveio/phik/blob/HEAD/pyproject.toml))
* [clang-format](https://pypi.org/project/clang-format) ([source](https://github.com/ssciwr/clang-format-wheel/blob/HEAD/pyproject.toml))
* [llama-cpp-python](https://pypi.org/project/llama-cpp-python) ([source](https://github.com/abetlen/llama-cpp-python/blob/HEAD/pyproject.toml))
* [coreforecast](https://pypi.org/project/coreforecast) ([source](https://github.com/Nixtla/coreforecast/blob/HEAD/pyproject.toml))
* [sparse-dot-topn](https://pypi.org/project/sparse-dot-topn) ([source](https://github.com/ing-bank/sparse_dot_topn/blob/HEAD/pyproject.toml))
* [spglib](https://pypi.org/project/spglib) ([source](https://github.com/spglib/spglib/blob/HEAD/pyproject.toml))
* [awkward-cpp](https://pypi.org/project/awkward-cpp) ([source](https://github.com/scikit-hep/awkward/blob/HEAD/awkward-cpp/pyproject.toml))
* [OpenEXR](https://pypi.org/project/OpenEXR) ([source](https://github.com/AcademySoftwareFoundation/OpenEXR/blob/HEAD/pyproject.toml))
* [iminuit](https://pypi.org/project/iminuit) ([source](https://github.com/scikit-hep/iminuit/blob/HEAD/pyproject.toml))
* [boost-histogram](https://pypi.org/project/boost-histogram) ([source](https://github.com/scikit-hep/iminuit/blob/HEAD/pyproject.toml))
* [astyle](https://pypi.org/project/astyle) ([source](https://github.com/Freed-Wu/astyle-wheel/blob/HEAD/pyproject.toml))
* [lammps](https://pypi.org/project/lammps) ([source](https://github.com/njzjz/lammps-wheel/blob/HEAD/pyproject.toml))
* [llamacpp](https://pypi.org/project/llamacpp) ([source](https://github.com/thomasantony/llamacpp-python/blob/HEAD/pyproject.toml))
* [nodejs-wheel](https://pypi.org/project/nodejs-wheel) ([source](https://github.com/njzjz/nodejs-wheel/blob/HEAD/pyproject.toml))
* [pygram11](https://pypi.org/project/pygram11) ([source](https://github.com/douglasdavis/pygram11/blob/HEAD/pyproject.toml))
* [manifold3d](https://pypi.org/project/manifold3d) ([source](https://github.com/elalish/manifold/blob/HEAD/pyproject.toml))
* [highspy](https://pypi.org/project/highspy) ([source](https://github.com/ERGO-Code/HiGHS/blob/HEAD/pyproject.toml))
* [laszip](https://pypi.org/project/laszip) ([source](https://github.com/tmontaigu/laszip-python/blob/HEAD/pyproject.toml))
* [imgui-bundle](https://pypi.org/project/imgui-bundle) ([source](https://github.com/pthom/imgui_bundle/blob/HEAD/pyproject.toml))
* [pyopencl](https://pypi.org/project/pyopencl) ([source](https://github.com/inducer/pyopencl/blob/HEAD/pyproject.toml))
* [pylibmagic](https://pypi.org/project/pylibmagic) ([source](https://github.com/kratsg/pylibmagic/blob/HEAD/pyproject.toml))
* [gemmi](https://pypi.org/project/gemmi) ([source](https://github.com/project-gemmi/gemmi/blob/HEAD/pyproject.toml))
* [gdstk](https://pypi.org/project/gdstk) ([source](https://github.com/heitzmann/gdstk/blob/HEAD/pyproject.toml))
* [symusic](https://pypi.org/project/symusic) ([source](https://github.com/Yikai-Liao/symusic/blob/HEAD/pyproject.toml))
* [s5cmd](https://pypi.org/project/s5cmd) ([source](https://github.com/ImagingDataCommons/s5cmd-python-distributions/blob/HEAD/pyproject.toml))
* [pyslang](https://pypi.org/project/pyslang) ([source](https://github.com/MikePopoloski/slang/blob/HEAD/pyproject.toml))
* [librapid](https://pypi.org/project/librapid) ([source](https://github.com/LibRapid/librapid/blob/HEAD/pyproject.toml))
* [pyresidfp](https://pypi.org/project/pyresidfp) ([source](https://github.com/pyresidfp/pyresidfp/blob/HEAD/pyproject.toml))
* [kiss-icp](https://pypi.org/project/kiss-icp) ([source](https://github.com/PRBonn/kiss-icp/blob/HEAD/python/pyproject.toml))
* [simsopt](https://pypi.org/project/simsopt) ([source](https://github.com/hiddenSymmetries/simsopt/blob/HEAD/pyproject.toml))
* [mqt-core](https://pypi.org/project/mqt-core) ([source](https://github.com/munich-quantum-toolkit/core/blob/HEAD/pyproject.toml))
<!--[[[end]]] (checksum: a798ae9bb220ab16cfe9402431cde0cf)-->

<!-- prettier-ignore-end -->

In addition, most of the [RAPIDSAI](https://github.com/rapidsai) projects use
scikit-build-core, but they are not published on PyPI. A few of them are:

- CuDF
  ([source](https://github.com/rapidsai/cudf/blob/HEAD/python/cudf/pyproject.toml))
- CuGraph
  ([source](https://github.com/rapidsai/cugraph/blob/HEAD/python/cugraph/pyproject.toml))
- CuML
  ([source](https://github.com/rapidsai/cuml/blob/HEAD/python/cuml/pyproject.toml))
- CuSpatial
  ([source](https://github.com/rapidsai/cuspatial/blob/HEAD/python/cuspatial/pyproject.toml))
- RMM
  ([source](https://github.com/rapidsai/rmm/blob/HEAD/python/rmm/pyproject.toml))
- Raft
  ([source](https://github.com/rapidsai/raft/blob/HEAD/python/pylibraft/pyproject.toml))

The [Insight Toolkit (ITK)](https://docs.itk.org), the initial target project
for scikit-build classic, has
[transitioned to sckit-build-core](https://github.com/InsightSoftwareConsortium/ITKPythonPackage/blob/master/scripts/pyproject.toml.in).
ITK currently provides one example of a production SWIG-based deployment. In
addition, dozens of
[ITK-based extension packages are configured with scikit-build-core](https://github.com/topics/itk-module).
