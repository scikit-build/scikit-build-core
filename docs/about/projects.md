# Projects

There are well over 600 projects using scikit-build-core on PyPI. This is a
selection of some of the projects. Feel free to add your own project to
`docs/data/projects.toml`. The following selection was primarily constructed by
looking at the [top 15,000](https://hugovk.dev/top-pypi-packages/) most
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
* [adios2](https://pypi.org/project/adios2) ([source](https://github.com/ornladios/ADIOS2/blob/HEAD/pyproject.toml))
* [afdko](https://pypi.org/project/afdko) ([source](https://github.com/adobe-type-tools/afdko/blob/HEAD/pyproject.toml))
* [ale-py](https://pypi.org/project/ale-py) ([source](https://github.com/Farama-Foundation/Arcade-Learning-Environment/blob/HEAD/pyproject.toml))
* [antspyx](https://pypi.org/project/antspyx) ([source](https://github.com/ANTsX/ANTsPy/blob/HEAD/pyproject.toml))
* [astyle](https://pypi.org/project/astyle) ([source](https://github.com/Freed-Wu/astyle-wheel/blob/HEAD/pyproject.toml))
* [awkward-cpp](https://pypi.org/project/awkward-cpp) ([source](https://github.com/scikit-hep/awkward/blob/HEAD/awkward-cpp/pyproject.toml))
* [bitsandbytes](https://pypi.org/project/bitsandbytes) ([source](https://github.com/bitsandbytes-foundation/bitsandbytes/blob/HEAD/pyproject.toml))
* [boost-histogram](https://pypi.org/project/boost-histogram) ([source](https://github.com/scikit-hep/boost-histogram/blob/HEAD/pyproject.toml))
* [celerite2](https://pypi.org/project/celerite2) ([source](https://github.com/exoplanet-dev/celerite2/blob/HEAD/pyproject.toml))
* [clang-format](https://pypi.org/project/clang-format) ([source](https://github.com/ssciwr/clang-format-wheel/blob/HEAD/pyproject.toml))
* [cmake](https://pypi.org/project/cmake) ([source](https://github.com/scikit-build/cmake-python-distributions/blob/HEAD/pyproject.toml))
* [CoolProp](https://pypi.org/project/CoolProp) ([source](https://github.com/CoolProp/CoolProp/blob/HEAD/pyproject.toml))
* [coreforecast](https://pypi.org/project/coreforecast) ([source](https://github.com/Nixtla/coreforecast/blob/HEAD/pyproject.toml))
* [deflate](https://pypi.org/project/deflate) ([source](https://github.com/dcwatson/deflate/blob/HEAD/pyproject.toml))
* [ducc0](https://pypi.org/project/ducc0) ([source](https://github.com/mreineck/ducc/blob/HEAD/pyproject.toml))
* [faiss-cpu](https://pypi.org/project/faiss-cpu) ([source](https://github.com/facebookresearch/faiss/blob/HEAD/pyproject.toml))
* [fandango-fuzzer](https://pypi.org/project/fandango-fuzzer) ([source](https://github.com/fandango-fuzzer/fandango/blob/HEAD/pyproject.toml))
* [freud-analysis](https://pypi.org/project/freud-analysis) ([source](https://github.com/glotzerlab/freud/blob/HEAD/pyproject.toml))
* [gdstk](https://pypi.org/project/gdstk) ([source](https://github.com/heitzmann/gdstk/blob/HEAD/pyproject.toml))
* [gemmi](https://pypi.org/project/gemmi) ([source](https://github.com/project-gemmi/gemmi/blob/HEAD/pyproject.toml))
* [h3](https://pypi.org/project/h3) ([source](https://github.com/uber/h3-py/blob/HEAD/pyproject.toml))
* [halide](https://pypi.org/project/halide) ([source](https://github.com/halide/Halide/blob/HEAD/pyproject.toml))
* [highspy](https://pypi.org/project/highspy) ([source](https://github.com/ERGO-Code/HiGHS/blob/HEAD/pyproject.toml))
* [imgui-bundle](https://pypi.org/project/imgui-bundle) ([source](https://github.com/pthom/imgui_bundle/blob/HEAD/pyproject.toml))
* [iminuit](https://pypi.org/project/iminuit) ([source](https://github.com/scikit-hep/iminuit/blob/HEAD/pyproject.toml))
* [implicit](https://pypi.org/project/implicit) ([source](https://github.com/benfred/implicit/blob/HEAD/pyproject.toml))
* [islpy](https://pypi.org/project/islpy) ([source](https://github.com/inducer/islpy/blob/HEAD/pyproject.toml))
* [JPype1](https://pypi.org/project/JPype1) ([source](https://github.com/jpype-project/jpype/blob/HEAD/pyproject.toml))
* [kiss-icp](https://pypi.org/project/kiss-icp) ([source](https://github.com/PRBonn/kiss-icp/blob/HEAD/python/pyproject.toml))
* [lammps](https://pypi.org/project/lammps) ([source](https://github.com/njzjz/lammps-wheel/blob/HEAD/pyproject.toml))
* [laszip](https://pypi.org/project/laszip) ([source](https://github.com/tmontaigu/laszip-python/blob/HEAD/pyproject.toml))
* [Levenshtein](https://pypi.org/project/Levenshtein) ([source](https://github.com/maxbachmann/Levenshtein/blob/HEAD/pyproject.toml))
* [libigl](https://pypi.org/project/libigl) ([source](https://github.com/libigl/libigl-python-bindings/blob/HEAD/pyproject.toml))
* [librapid](https://pypi.org/project/librapid) ([source](https://github.com/LibRapid/librapid/blob/HEAD/pyproject.toml))
* [lightgbm](https://pypi.org/project/lightgbm) ([source](https://github.com/lightgbm-org/LightGBM/blob/HEAD/python-package/pyproject.toml))
* [llama-cpp-python](https://pypi.org/project/llama-cpp-python) ([source](https://github.com/abetlen/llama-cpp-python/blob/HEAD/pyproject.toml))
* [llamacpp](https://pypi.org/project/llamacpp) ([source](https://github.com/thomasantony/llamacpp-python/blob/HEAD/pyproject.toml))
* [manifold3d](https://pypi.org/project/manifold3d) ([source](https://github.com/elalish/manifold/blob/HEAD/pyproject.toml))
* [MaterialX](https://pypi.org/project/MaterialX) ([source](https://github.com/AcademySoftwareFoundation/MaterialX/blob/HEAD/pyproject.toml))
* [mitsuba](https://pypi.org/project/mitsuba) ([source](https://github.com/mitsuba-renderer/mitsuba3/blob/HEAD/pyproject.toml))
* [mqt-core](https://pypi.org/project/mqt-core) ([source](https://github.com/munich-quantum-toolkit/core/blob/HEAD/pyproject.toml))
* [nanobind](https://pypi.org/project/nanobind) ([source](https://github.com/wjakob/nanobind/blob/HEAD/pyproject.toml))
* [ncrystal](https://pypi.org/project/ncrystal) ([source](https://github.com/mctools/ncrystal/blob/HEAD/pyproject.toml))
* [ninja](https://pypi.org/project/ninja) ([source](https://github.com/scikit-build/ninja-python-distributions/blob/HEAD/pyproject.toml))
* [nodejs-wheel](https://pypi.org/project/nodejs-wheel) ([source](https://github.com/njzjz/nodejs-wheel/blob/HEAD/pyproject.toml))
* [ompl](https://pypi.org/project/ompl) ([source](https://github.com/ompl/ompl/blob/HEAD/py-bindings/pyproject.toml))
* [onnx](https://pypi.org/project/onnx) ([source](https://github.com/onnx/onnx/blob/HEAD/pyproject.toml))
* [OpenEXR](https://pypi.org/project/OpenEXR) ([source](https://github.com/AcademySoftwareFoundation/OpenEXR/blob/HEAD/pyproject.toml))
* [OpenImageIO](https://pypi.org/project/OpenImageIO) ([source](https://github.com/AcademySoftwareFoundation/OpenImageIO/blob/HEAD/pyproject.toml))
* [osmium](https://pypi.org/project/osmium) ([source](https://github.com/osmcode/pyosmium/blob/HEAD/pyproject.toml))
* [osqp](https://pypi.org/project/osqp) ([source](https://github.com/osqp/osqp-python/blob/HEAD/pyproject.toml))
* [pedalboard](https://pypi.org/project/pedalboard) ([source](https://github.com/spotify/pedalboard/blob/HEAD/pyproject.toml))
* [phik](https://pypi.org/project/phik) ([source](https://github.com/kaveio/phik/blob/HEAD/pyproject.toml))
* [phono3py](https://pypi.org/project/phono3py) ([source](https://github.com/phonopy/phono3py/blob/HEAD/pyproject.toml))
* [phonopy](https://pypi.org/project/phonopy) ([source](https://github.com/phonopy/phonopy/blob/HEAD/pyproject.toml))
* [pikepdf](https://pypi.org/project/pikepdf) ([source](https://github.com/pikepdf/pikepdf/blob/HEAD/pyproject.toml))
* [polyscope](https://pypi.org/project/polyscope) ([source](https://github.com/nmwsharp/polyscope-py/blob/HEAD/pyproject.toml))
* [pyarrow](https://pypi.org/project/pyarrow) ([source](https://github.com/apache/arrow/blob/HEAD/python/pyproject.toml))
* [pybind11](https://pypi.org/project/pybind11) ([source](https://github.com/pybind/pybind11/blob/HEAD/pyproject.toml))
* [pycolmap](https://pypi.org/project/pycolmap) ([source](https://github.com/colmap/colmap/blob/HEAD/pyproject.toml))
* [pygram11](https://pypi.org/project/pygram11) ([source](https://github.com/douglasdavis/pygram11/blob/HEAD/pyproject.toml))
* [pyhmmer](https://pypi.org/project/pyhmmer) ([source](https://github.com/althonos/pyhmmer/blob/HEAD/pyproject.toml))
* [pylibmagic](https://pypi.org/project/pylibmagic) ([source](https://github.com/kratsg/pylibmagic/blob/HEAD/pyproject.toml))
* [pyopencl](https://pypi.org/project/pyopencl) ([source](https://github.com/inducer/pyopencl/blob/HEAD/pyproject.toml))
* [pyradiomics](https://pypi.org/project/pyradiomics) ([source](https://github.com/AIM-Harvard/pyradiomics/blob/HEAD/pyproject.toml))
* [pyresidfp](https://pypi.org/project/pyresidfp) ([source](https://github.com/pyresidfp/pyresidfp/blob/HEAD/pyproject.toml))
* [pyslang](https://pypi.org/project/pyslang) ([source](https://github.com/MikePopoloski/slang/blob/HEAD/pyproject.toml))
* [pyzmq](https://pypi.org/project/pyzmq) ([source](https://github.com/zeromq/pyzmq/blob/HEAD/pyproject.toml))
* [rapidfuzz](https://pypi.org/project/rapidfuzz) ([source](https://github.com/rapidfuzz/RapidFuzz/blob/HEAD/pyproject.toml))
* [roboticstoolbox-python](https://pypi.org/project/roboticstoolbox-python) ([source](https://github.com/petercorke/robotics-toolbox-python/blob/HEAD/pyproject.toml))
* [root](https://pypi.org/project/root) ([source](https://github.com/root-project/root/blob/HEAD/pyproject.toml))
* [s5cmd](https://pypi.org/project/s5cmd) ([source](https://github.com/ImagingDataCommons/s5cmd-python-distributions/blob/HEAD/pyproject.toml))
* [shap](https://pypi.org/project/shap) ([source](https://github.com/shap/shap/blob/HEAD/pyproject.toml))
* [SimpleITK](https://pypi.org/project/SimpleITK) ([source](https://github.com/SimpleITK/SimpleITK/blob/HEAD/pyproject.toml))
* [simsopt](https://pypi.org/project/simsopt) ([source](https://github.com/hiddenSymmetries/simsopt/blob/HEAD/pyproject.toml))
* [sparse-dot-topn](https://pypi.org/project/sparse-dot-topn) ([source](https://github.com/ing-bank/sparse_dot_topn/blob/HEAD/pyproject.toml))
* [spglib](https://pypi.org/project/spglib) ([source](https://github.com/spglib/spglib/blob/HEAD/pyproject.toml))
* [spherely](https://pypi.org/project/spherely) ([source](https://github.com/benbovy/spherely/blob/HEAD/pyproject.toml))
* [stormpy](https://pypi.org/project/stormpy) ([source](https://github.com/stormchecker/stormpy/blob/HEAD/pyproject.toml))
* [symusic](https://pypi.org/project/symusic) ([source](https://github.com/Yikai-Liao/symusic/blob/HEAD/pyproject.toml))
* [tetgen](https://pypi.org/project/tetgen) ([source](https://github.com/pyvista/tetgen/blob/HEAD/pyproject.toml))
* [tiledb](https://pypi.org/project/tiledb) ([source](https://github.com/TileDB-Inc/TileDB-Py/blob/HEAD/pyproject.toml))
* [tomotopy](https://pypi.org/project/tomotopy) ([source](https://github.com/bab2min/tomotopy/blob/HEAD/pyproject.toml))
* [viennals](https://pypi.org/project/viennals) ([source](https://github.com/ViennaTools/ViennaLS/blob/HEAD/pyproject.toml))
* [viennaps](https://pypi.org/project/viennaps) ([source](https://github.com/ViennaTools/ViennaPS/blob/HEAD/pyproject.toml))
* [voyager](https://pypi.org/project/voyager) ([source](https://github.com/spotify/voyager/blob/HEAD/python/pyproject.toml))
* [xgrammar](https://pypi.org/project/xgrammar) ([source](https://github.com/mlc-ai/xgrammar/blob/HEAD/pyproject.toml))
* [xtgeo](https://pypi.org/project/xtgeo) ([source](https://github.com/equinor/xtgeo/blob/HEAD/pyproject.toml))
<!--[[[end]]] (sum: aPoX60a7Kd)-->

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
[transitioned to scikit-build-core](https://github.com/InsightSoftwareConsortium/ITKPythonPackage/blob/master/scripts/pyproject.toml.in).
ITK currently provides one example of a production SWIG-based deployment. In
addition, dozens of
[ITK-based extension packages are configured with scikit-build-core](https://github.com/topics/itk-module).
