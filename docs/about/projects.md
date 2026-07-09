# Projects

There are well over 600 projects using scikit-build-core on PyPI. This is a
selection of some of the projects. Feel free to add your own project to
`docs/data/projects.toml`. The following selection was primarily constructed by
looking at the [top 15,000](https://hugovk.dev/top-pypi-packages/) most
downloaded projects on PyPI for top-level pyproject.toml's in SDists that use
scikit-build-core.

<!-- prettier-ignore-start -->

:::{container} project-grid

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

    entry = f'* [{pypi}](https://pypi.org/project/{pypi}) [GitHub](https://github.com/{github}/blob/HEAD/{path} "{github}"){{.sk-src}}'
    badges = [f"`{lang.strip()}`{{.sk-lang}}" for lang in project.get("language", "").split(",") if lang.strip()]
    badges += [f"`{tool.strip()}`{{.sk-tool}}" for tool in project.get("binding", "").split(",") if tool.strip()]
    if badges:
        entry += "\n  " + " ".join(badges)
    cog.outl(entry)
]]]-->
* [adios2](https://pypi.org/project/adios2) [GitHub](https://github.com/ornladios/ADIOS2/blob/HEAD/pyproject.toml "ornladios/ADIOS2"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [afdko](https://pypi.org/project/afdko) [GitHub](https://github.com/adobe-type-tools/afdko/blob/HEAD/pyproject.toml "adobe-type-tools/afdko"){.sk-src}
  `C`{.sk-lang} `C++`{.sk-lang} `Cython`{.sk-tool}
* [ale-py](https://pypi.org/project/ale-py) [GitHub](https://github.com/Farama-Foundation/Arcade-Learning-Environment/blob/HEAD/pyproject.toml "Farama-Foundation/Arcade-Learning-Environment"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [antspyx](https://pypi.org/project/antspyx) [GitHub](https://github.com/ANTsX/ANTsPy/blob/HEAD/pyproject.toml "ANTsX/ANTsPy"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [astyle](https://pypi.org/project/astyle) [GitHub](https://github.com/Freed-Wu/astyle-wheel/blob/HEAD/pyproject.toml "Freed-Wu/astyle-wheel"){.sk-src}
  `C++`{.sk-lang}
* [awkward-cpp](https://pypi.org/project/awkward-cpp) [GitHub](https://github.com/scikit-hep/awkward/blob/HEAD/awkward-cpp/pyproject.toml "scikit-hep/awkward"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [bitsandbytes](https://pypi.org/project/bitsandbytes) [GitHub](https://github.com/bitsandbytes-foundation/bitsandbytes/blob/HEAD/pyproject.toml "bitsandbytes-foundation/bitsandbytes"){.sk-src}
  `C++`{.sk-lang} `CUDA`{.sk-lang} `ctypes`{.sk-tool}
* [boost-histogram](https://pypi.org/project/boost-histogram) [GitHub](https://github.com/scikit-hep/boost-histogram/blob/HEAD/pyproject.toml "scikit-hep/boost-histogram"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [celerite2](https://pypi.org/project/celerite2) [GitHub](https://github.com/exoplanet-dev/celerite2/blob/HEAD/pyproject.toml "exoplanet-dev/celerite2"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [clang-format](https://pypi.org/project/clang-format) [GitHub](https://github.com/ssciwr/clang-format-wheel/blob/HEAD/pyproject.toml "ssciwr/clang-format-wheel"){.sk-src}
  `C++`{.sk-lang}
* [cmake](https://pypi.org/project/cmake) [GitHub](https://github.com/scikit-build/cmake-python-distributions/blob/HEAD/pyproject.toml "scikit-build/cmake-python-distributions"){.sk-src}
  `C++`{.sk-lang}
* [CoolProp](https://pypi.org/project/CoolProp) [GitHub](https://github.com/CoolProp/CoolProp/blob/HEAD/pyproject.toml "CoolProp/CoolProp"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [coreforecast](https://pypi.org/project/coreforecast) [GitHub](https://github.com/Nixtla/coreforecast/blob/HEAD/pyproject.toml "Nixtla/coreforecast"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [deflate](https://pypi.org/project/deflate) [GitHub](https://github.com/dcwatson/deflate/blob/HEAD/pyproject.toml "dcwatson/deflate"){.sk-src}
  `C`{.sk-lang} `C API`{.sk-tool}
* [ducc0](https://pypi.org/project/ducc0) [GitHub](https://github.com/mreineck/ducc/blob/HEAD/pyproject.toml "mreineck/ducc"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [faiss-cpu](https://pypi.org/project/faiss-cpu) [GitHub](https://github.com/facebookresearch/faiss/blob/HEAD/pyproject.toml "facebookresearch/faiss"){.sk-src}
  `C++`{.sk-lang} `SWIG`{.sk-tool}
* [fandango-fuzzer](https://pypi.org/project/fandango-fuzzer) [GitHub](https://github.com/fandango-fuzzer/fandango/blob/HEAD/pyproject.toml "fandango-fuzzer/fandango"){.sk-src}
  `C++`{.sk-lang} `C API`{.sk-tool}
* [freud-analysis](https://pypi.org/project/freud-analysis) [GitHub](https://github.com/glotzerlab/freud/blob/HEAD/pyproject.toml "glotzerlab/freud"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [gdstk](https://pypi.org/project/gdstk) [GitHub](https://github.com/heitzmann/gdstk/blob/HEAD/pyproject.toml "heitzmann/gdstk"){.sk-src}
  `C++`{.sk-lang} `C API`{.sk-tool}
* [gemmi](https://pypi.org/project/gemmi) [GitHub](https://github.com/project-gemmi/gemmi/blob/HEAD/pyproject.toml "project-gemmi/gemmi"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [h3](https://pypi.org/project/h3) [GitHub](https://github.com/uber/h3-py/blob/HEAD/pyproject.toml "uber/h3-py"){.sk-src}
  `C`{.sk-lang} `Cython`{.sk-tool}
* [halide](https://pypi.org/project/halide) [GitHub](https://github.com/halide/Halide/blob/HEAD/pyproject.toml "halide/Halide"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [highspy](https://pypi.org/project/highspy) [GitHub](https://github.com/ERGO-Code/HiGHS/blob/HEAD/pyproject.toml "ERGO-Code/HiGHS"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [imgui-bundle](https://pypi.org/project/imgui-bundle) [GitHub](https://github.com/pthom/imgui_bundle/blob/HEAD/pyproject.toml "pthom/imgui_bundle"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [iminuit](https://pypi.org/project/iminuit) [GitHub](https://github.com/scikit-hep/iminuit/blob/HEAD/pyproject.toml "scikit-hep/iminuit"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [implicit](https://pypi.org/project/implicit) [GitHub](https://github.com/benfred/implicit/blob/HEAD/pyproject.toml "benfred/implicit"){.sk-src}
  `C++`{.sk-lang} `CUDA`{.sk-lang} `Cython`{.sk-tool}
* [islpy](https://pypi.org/project/islpy) [GitHub](https://github.com/inducer/islpy/blob/HEAD/pyproject.toml "inducer/islpy"){.sk-src}
  `C`{.sk-lang} `nanobind`{.sk-tool}
* [JPype1](https://pypi.org/project/JPype1) [GitHub](https://github.com/jpype-project/jpype/blob/HEAD/pyproject.toml "jpype-project/jpype"){.sk-src}
  `C++`{.sk-lang} `C API`{.sk-tool}
* [kiss-icp](https://pypi.org/project/kiss-icp) [GitHub](https://github.com/PRBonn/kiss-icp/blob/HEAD/python/pyproject.toml "PRBonn/kiss-icp"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [lammps](https://pypi.org/project/lammps) [GitHub](https://github.com/njzjz/lammps-wheel/blob/HEAD/pyproject.toml "njzjz/lammps-wheel"){.sk-src}
  `C++`{.sk-lang} `ctypes`{.sk-tool}
* [laszip](https://pypi.org/project/laszip) [GitHub](https://github.com/tmontaigu/laszip-python/blob/HEAD/pyproject.toml "tmontaigu/laszip-python"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [Levenshtein](https://pypi.org/project/Levenshtein) [GitHub](https://github.com/maxbachmann/Levenshtein/blob/HEAD/pyproject.toml "maxbachmann/Levenshtein"){.sk-src}
  `C++`{.sk-lang} `Cython`{.sk-tool}
* [libigl](https://pypi.org/project/libigl) [GitHub](https://github.com/libigl/libigl-python-bindings/blob/HEAD/pyproject.toml "libigl/libigl-python-bindings"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [librapid](https://pypi.org/project/librapid) [GitHub](https://github.com/LibRapid/librapid/blob/HEAD/pyproject.toml "LibRapid/librapid"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [lightgbm](https://pypi.org/project/lightgbm) [GitHub](https://github.com/lightgbm-org/LightGBM/blob/HEAD/python-package/pyproject.toml "lightgbm-org/LightGBM"){.sk-src}
  `C++`{.sk-lang} `ctypes`{.sk-tool}
* [llama-cpp-python](https://pypi.org/project/llama-cpp-python) [GitHub](https://github.com/abetlen/llama-cpp-python/blob/HEAD/pyproject.toml "abetlen/llama-cpp-python"){.sk-src}
  `C++`{.sk-lang} `ctypes`{.sk-tool}
* [llamacpp](https://pypi.org/project/llamacpp) [GitHub](https://github.com/thomasantony/llamacpp-python/blob/HEAD/pyproject.toml "thomasantony/llamacpp-python"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [manifold3d](https://pypi.org/project/manifold3d) [GitHub](https://github.com/elalish/manifold/blob/HEAD/pyproject.toml "elalish/manifold"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [MaterialX](https://pypi.org/project/MaterialX) [GitHub](https://github.com/AcademySoftwareFoundation/MaterialX/blob/HEAD/pyproject.toml "AcademySoftwareFoundation/MaterialX"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [mitsuba](https://pypi.org/project/mitsuba) [GitHub](https://github.com/mitsuba-renderer/mitsuba3/blob/HEAD/pyproject.toml "mitsuba-renderer/mitsuba3"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [mqt-core](https://pypi.org/project/mqt-core) [GitHub](https://github.com/munich-quantum-toolkit/core/blob/HEAD/pyproject.toml "munich-quantum-toolkit/core"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [nanobind](https://pypi.org/project/nanobind) [GitHub](https://github.com/wjakob/nanobind/blob/HEAD/pyproject.toml "wjakob/nanobind"){.sk-src}
  `C++`{.sk-lang}
* [ncrystal](https://pypi.org/project/ncrystal) [GitHub](https://github.com/mctools/ncrystal/blob/HEAD/pyproject.toml "mctools/ncrystal"){.sk-src}
  `C++`{.sk-lang} `C`{.sk-lang} `ctypes`{.sk-tool}
* [ninja](https://pypi.org/project/ninja) [GitHub](https://github.com/scikit-build/ninja-python-distributions/blob/HEAD/pyproject.toml "scikit-build/ninja-python-distributions"){.sk-src}
  `C++`{.sk-lang}
* [nodejs-wheel](https://pypi.org/project/nodejs-wheel) [GitHub](https://github.com/njzjz/nodejs-wheel/blob/HEAD/pyproject.toml "njzjz/nodejs-wheel"){.sk-src}
  `C++`{.sk-lang}
* [ompl](https://pypi.org/project/ompl) [GitHub](https://github.com/ompl/ompl/blob/HEAD/py-bindings/pyproject.toml "ompl/ompl"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [onnx](https://pypi.org/project/onnx) [GitHub](https://github.com/onnx/onnx/blob/HEAD/pyproject.toml "onnx/onnx"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [OpenEXR](https://pypi.org/project/OpenEXR) [GitHub](https://github.com/AcademySoftwareFoundation/OpenEXR/blob/HEAD/pyproject.toml "AcademySoftwareFoundation/OpenEXR"){.sk-src}
  `C++`{.sk-lang} `C`{.sk-lang} `pybind11`{.sk-tool}
* [OpenImageIO](https://pypi.org/project/OpenImageIO) [GitHub](https://github.com/AcademySoftwareFoundation/OpenImageIO/blob/HEAD/pyproject.toml "AcademySoftwareFoundation/OpenImageIO"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [osmium](https://pypi.org/project/osmium) [GitHub](https://github.com/osmcode/pyosmium/blob/HEAD/pyproject.toml "osmcode/pyosmium"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [osqp](https://pypi.org/project/osqp) [GitHub](https://github.com/osqp/osqp-python/blob/HEAD/pyproject.toml "osqp/osqp-python"){.sk-src}
  `C`{.sk-lang} `pybind11`{.sk-tool}
* [pedalboard](https://pypi.org/project/pedalboard) [GitHub](https://github.com/spotify/pedalboard/blob/HEAD/pyproject.toml "spotify/pedalboard"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [phik](https://pypi.org/project/phik) [GitHub](https://github.com/kaveio/phik/blob/HEAD/pyproject.toml "kaveio/phik"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [phono3py](https://pypi.org/project/phono3py) [GitHub](https://github.com/phonopy/phono3py/blob/HEAD/pyproject.toml "phonopy/phono3py"){.sk-src}
  `C`{.sk-lang} `nanobind`{.sk-tool}
* [phonopy](https://pypi.org/project/phonopy) [GitHub](https://github.com/phonopy/phonopy/blob/HEAD/pyproject.toml "phonopy/phonopy"){.sk-src}
  `C`{.sk-lang} `nanobind`{.sk-tool}
* [pikepdf](https://pypi.org/project/pikepdf) [GitHub](https://github.com/pikepdf/pikepdf/blob/HEAD/pyproject.toml "pikepdf/pikepdf"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [polyscope](https://pypi.org/project/polyscope) [GitHub](https://github.com/nmwsharp/polyscope-py/blob/HEAD/pyproject.toml "nmwsharp/polyscope-py"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [pyarrow](https://pypi.org/project/pyarrow) [GitHub](https://github.com/apache/arrow/blob/HEAD/python/pyproject.toml "apache/arrow"){.sk-src}
  `C++`{.sk-lang} `Cython`{.sk-tool}
* [pybind11](https://pypi.org/project/pybind11) [GitHub](https://github.com/pybind/pybind11/blob/HEAD/pyproject.toml "pybind/pybind11"){.sk-src}
  `C++`{.sk-lang}
* [pycolmap](https://pypi.org/project/pycolmap) [GitHub](https://github.com/colmap/colmap/blob/HEAD/pyproject.toml "colmap/colmap"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [pygram11](https://pypi.org/project/pygram11) [GitHub](https://github.com/douglasdavis/pygram11/blob/HEAD/pyproject.toml "douglasdavis/pygram11"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [pyhmmer](https://pypi.org/project/pyhmmer) [GitHub](https://github.com/althonos/pyhmmer/blob/HEAD/pyproject.toml "althonos/pyhmmer"){.sk-src}
  `C`{.sk-lang} `Cython`{.sk-tool}
* [pylibmagic](https://pypi.org/project/pylibmagic) [GitHub](https://github.com/kratsg/pylibmagic/blob/HEAD/pyproject.toml "kratsg/pylibmagic"){.sk-src}
  `C`{.sk-lang}
* [pyopencl](https://pypi.org/project/pyopencl) [GitHub](https://github.com/inducer/pyopencl/blob/HEAD/pyproject.toml "inducer/pyopencl"){.sk-src}
  `C++`{.sk-lang} `C`{.sk-lang} `nanobind`{.sk-tool}
* [pyradiomics](https://pypi.org/project/pyradiomics) [GitHub](https://github.com/AIM-Harvard/pyradiomics/blob/HEAD/pyproject.toml "AIM-Harvard/pyradiomics"){.sk-src}
  `C`{.sk-lang} `C API`{.sk-tool}
* [pyresidfp](https://pypi.org/project/pyresidfp) [GitHub](https://github.com/pyresidfp/pyresidfp/blob/HEAD/pyproject.toml "pyresidfp/pyresidfp"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [pyslang](https://pypi.org/project/pyslang) [GitHub](https://github.com/MikePopoloski/slang/blob/HEAD/pyproject.toml "MikePopoloski/slang"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [pyzmq](https://pypi.org/project/pyzmq) [GitHub](https://github.com/zeromq/pyzmq/blob/HEAD/pyproject.toml "zeromq/pyzmq"){.sk-src}
  `C`{.sk-lang} `Cython`{.sk-tool}
* [rapidfuzz](https://pypi.org/project/rapidfuzz) [GitHub](https://github.com/rapidfuzz/RapidFuzz/blob/HEAD/pyproject.toml "rapidfuzz/RapidFuzz"){.sk-src}
  `C++`{.sk-lang} `Cython`{.sk-tool}
* [roboticstoolbox-python](https://pypi.org/project/roboticstoolbox-python) [GitHub](https://github.com/petercorke/robotics-toolbox-python/blob/HEAD/pyproject.toml "petercorke/robotics-toolbox-python"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [root](https://pypi.org/project/root) [GitHub](https://github.com/root-project/root/blob/HEAD/pyproject.toml "root-project/root"){.sk-src}
  `C++`{.sk-lang} `cppyy`{.sk-tool}
* [s5cmd](https://pypi.org/project/s5cmd) [GitHub](https://github.com/ImagingDataCommons/s5cmd-python-distributions/blob/HEAD/pyproject.toml "ImagingDataCommons/s5cmd-python-distributions"){.sk-src}
  `Go`{.sk-lang}
* [shap](https://pypi.org/project/shap) [GitHub](https://github.com/shap/shap/blob/HEAD/pyproject.toml "shap/shap"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [SimpleITK](https://pypi.org/project/SimpleITK) [GitHub](https://github.com/SimpleITK/SimpleITK/blob/HEAD/pyproject.toml "SimpleITK/SimpleITK"){.sk-src}
  `C++`{.sk-lang} `SWIG`{.sk-tool}
* [simsopt](https://pypi.org/project/simsopt) [GitHub](https://github.com/hiddenSymmetries/simsopt/blob/HEAD/pyproject.toml "hiddenSymmetries/simsopt"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [sparse-dot-topn](https://pypi.org/project/sparse-dot-topn) [GitHub](https://github.com/ing-bank/sparse_dot_topn/blob/HEAD/pyproject.toml "ing-bank/sparse_dot_topn"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [spglib](https://pypi.org/project/spglib) [GitHub](https://github.com/spglib/spglib/blob/HEAD/pyproject.toml "spglib/spglib"){.sk-src}
  `C`{.sk-lang} `pybind11`{.sk-tool}
* [spherely](https://pypi.org/project/spherely) [GitHub](https://github.com/benbovy/spherely/blob/HEAD/pyproject.toml "benbovy/spherely"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [stormpy](https://pypi.org/project/stormpy) [GitHub](https://github.com/stormchecker/stormpy/blob/HEAD/pyproject.toml "stormchecker/stormpy"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [symusic](https://pypi.org/project/symusic) [GitHub](https://github.com/Yikai-Liao/symusic/blob/HEAD/pyproject.toml "Yikai-Liao/symusic"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [tetgen](https://pypi.org/project/tetgen) [GitHub](https://github.com/pyvista/tetgen/blob/HEAD/pyproject.toml "pyvista/tetgen"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [tiledb](https://pypi.org/project/tiledb) [GitHub](https://github.com/TileDB-Inc/TileDB-Py/blob/HEAD/pyproject.toml "TileDB-Inc/TileDB-Py"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [tomotopy](https://pypi.org/project/tomotopy) [GitHub](https://github.com/bab2min/tomotopy/blob/HEAD/pyproject.toml "bab2min/tomotopy"){.sk-src}
  `C++`{.sk-lang} `C API`{.sk-tool}
* [viennals](https://pypi.org/project/viennals) [GitHub](https://github.com/ViennaTools/ViennaLS/blob/HEAD/pyproject.toml "ViennaTools/ViennaLS"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [viennaps](https://pypi.org/project/viennaps) [GitHub](https://github.com/ViennaTools/ViennaPS/blob/HEAD/pyproject.toml "ViennaTools/ViennaPS"){.sk-src}
  `C++`{.sk-lang} `pybind11`{.sk-tool}
* [voyager](https://pypi.org/project/voyager) [GitHub](https://github.com/spotify/voyager/blob/HEAD/python/pyproject.toml "spotify/voyager"){.sk-src}
  `C++`{.sk-lang} `nanobind`{.sk-tool}
* [xgrammar](https://pypi.org/project/xgrammar) [GitHub](https://github.com/mlc-ai/xgrammar/blob/HEAD/pyproject.toml "mlc-ai/xgrammar"){.sk-src}
  `C++`{.sk-lang} `C API`{.sk-tool}
* [xtgeo](https://pypi.org/project/xtgeo) [GitHub](https://github.com/equinor/xtgeo/blob/HEAD/pyproject.toml "equinor/xtgeo"){.sk-src}
  `C`{.sk-lang} `C++`{.sk-lang} `pybind11`{.sk-tool} `SWIG`{.sk-tool}
<!--[[[end]]] (sum: fdPMxXZJHs)-->

:::

<!-- prettier-ignore-end -->

In addition, most of the [RAPIDSAI](https://github.com/rapidsai) projects use
scikit-build-core, but they are not published on PyPI. A few of them are:

:::{container} project-grid

- [CuDF](https://docs.rapids.ai/api/cudf/stable/)
  [GitHub](https://github.com/rapidsai/cudf/blob/HEAD/python/cudf/pyproject.toml "rapidsai/cudf"){.sk-src}
  `C++`{.sk-lang} `CUDA`{.sk-lang} `Cython`{.sk-tool}
- [CuGraph](https://docs.rapids.ai/api/cugraph/stable/)
  [GitHub](https://github.com/rapidsai/cugraph/blob/HEAD/python/cugraph/pyproject.toml "rapidsai/cugraph"){.sk-src}
  `C++`{.sk-lang} `CUDA`{.sk-lang} `Cython`{.sk-tool}
- [CuML](https://docs.rapids.ai/api/cuml/stable/)
  [GitHub](https://github.com/rapidsai/cuml/blob/HEAD/python/cuml/pyproject.toml "rapidsai/cuml"){.sk-src}
  `C++`{.sk-lang} `CUDA`{.sk-lang} `Cython`{.sk-tool}
- [CuSpatial](https://docs.rapids.ai/api/cuspatial/stable/)
  [GitHub](https://github.com/rapidsai/cuspatial/blob/HEAD/python/cuspatial/pyproject.toml "rapidsai/cuspatial"){.sk-src}
  `C++`{.sk-lang} `CUDA`{.sk-lang} `Cython`{.sk-tool}
- [RMM](https://docs.rapids.ai/api/rmm/stable/)
  [GitHub](https://github.com/rapidsai/rmm/blob/HEAD/python/rmm/pyproject.toml "rapidsai/rmm"){.sk-src}
  `C++`{.sk-lang} `CUDA`{.sk-lang} `Cython`{.sk-tool}
- [Raft](https://docs.rapids.ai/api/raft/stable/)
  [GitHub](https://github.com/rapidsai/raft/blob/HEAD/python/pylibraft/pyproject.toml "rapidsai/raft"){.sk-src}
  `C++`{.sk-lang} `CUDA`{.sk-lang} `Cython`{.sk-tool}

:::

The [Insight Toolkit (ITK)](https://docs.itk.org), the initial target project
for scikit-build classic, has
[transitioned to scikit-build-core](https://github.com/InsightSoftwareConsortium/ITKPythonPackage/blob/master/scripts/pyproject.toml.in).
ITK currently provides one example of a production SWIG-based deployment. In
addition, dozens of
[ITK-based extension packages are configured with scikit-build-core](https://github.com/topics/itk-module).
