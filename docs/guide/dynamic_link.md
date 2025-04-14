# Dynamic linking

If you want to support dynamic linkages between python projects or system
libraries, you will likely encounter some issues in making sure the compiled
libraries/python bindings work after the wheel is created and the python project
is installed on the system. The most common issue are the missing hints pointing
to where the runtime libraries are located, specifically `RPATH` on Linux and
MacOS systems, and `PATH`/`os.add_dll_directory` on Windows systems. Here are
some recommendations on how to address them.

## Link to the static libraries

The easiest solution is to make sure you link to the static libraries
counterparts during the CMake build. How to achieve this depends on the specific
dependency, how it is imported in the CMake project and how the dependency is
packaged in each ecosystem.

For example for [Boost][FindBoost] this is controlled via the variable
`Boost_USE_STATIC_LIBS`.

[FindBoost]: inv:cmake:cmake:module#module:FindBoost

## Wheel repair tools

There are wheel repair tools for each operating system that bundle any dynamic
libraries used and patch the libraries/python bindings to point to prioritize
those libraries. The most common tools for these are [auditwheel] for Linux,
[delocate] for MacOS and [delvewheel] for Windows. [cibuildwheel] incorporates
these tools in its [repair wheel] feature.

These tools also rename the library with a unique hash to avoid any potential
name collision if the same library is being bundled by a different package, and
check if the packages confirm to standards like [PEP600] (`manylinux_X_Y`).
These tools do not allow to have cross wheel library dependency.

## Manual patching

You can manually make a relative RPath. This has the benefit of working when not
running scikit-build-core, as well.

The `RPATH` patching can be done as

```cmake
if(APPLE)
  set(origin_token "@loader_path")
else()
  set(origin_token "$ORIGIN")
endif()
set_property(TARGET <target> PROPERTY INSTALL_RPATH
  "${origin_token}/install_path/to/dynamic_library"
)
```

For Windows patching, this has to be done at the python files using
`os.add_dll_directory` at the top-most package `__init__.py` file or top-level
python module files.

```python
import os
from pathlib import Path

dependency_dll_path = Path(__file__).parent / "install_path/to/dynamic_library"
os.add_dll_directory(str(dependency_dll_path))
```

<!-- prettier-ignore-start -->

[auditwheel]: https://pypi.org/project/auditwheel/
[delocate]: https://pypi.org/project/delocate/
[delvewheel]: https://pypi.org/project/delvewheel/
[cibuildwheel]: https://cibuildwheel.pypa.io/en/stable/
[repair wheel]: https://cibuildwheel.pypa.io/en/stable/options/#repair-wheel-command
[PEP600]: https://peps.python.org/pep-0600

<!-- prettier-ignore-end -->
