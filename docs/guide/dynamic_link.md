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

## scikit-build-core wheel repair

:::{warning}

This feature is experimental and API and effects may change.

:::

scikit-build-core also provides a built-in wheel repair which is enabled from
`wheel.repair.enable`. Unlike the [wheel repair tools], this feature uses the
linking information used during the CMake steps.

:::{note}

Executables, libraries, dependencies installed in `${SKBUILD_SCRIPTS_DIR}` or
`${SKBUILD_DATA_DIR}` are not considered. Only files in `wheel.install-dir` or
`${SKBUILD_PLATLIB_DIR}` are considered.

:::

So far there are 3 repair features implemented, which can be activated
independently.

### `wheel.repair.in-wheel`

If this feature is enabled, it patches the executable/libraries so that, if the
dependency is packaged in the _same_ wheel, the executable/libraries point to
the dependency files inside the wheel.

### `wheel.repair.cross-wheel`

If this feature is enabled, it patches the executable/libraries so that, if the
dependency is packaged in a _different_ wheel available from
`build-system.requires`, the executable/libraries point to the dependency files
in that other wheel.

The same/compatible library that was used in the `build-system.requires` should
be used in the project's dependencies. The link to the other wheel will have
priority, but if that wheel is not installed or is incompatible, it will
fall-through to the system dependencies.

### `wheel.repair.bundle-external`

This feature is enabled by providing a list of regex patterns of the dynamic
libraries that should be bundled. Only the filename is considered for the regex
matching. The dependency files are then copied to a folder `{project.name}.libs`
and the dependents are patched to point to there.

External libraries linked from a different wheel available from
`build-system.requires` are not considered.

:::{warning}

Unlike the [wheel repair tools], this feature does not mangle the library names,
which may cause issues if multiple dependencies link to the same library with
the same `SONAME`/`SOVERSION` (usually just the library file name).

:::

### Windows repairs

The windows wheel repairs are done by adding `os.add_dll_directory` commands to
the top-level python package/modules in the current wheel. Thus, the library
linkage is only available when executing a python script/module that import the
current wheel's top-level python package/modules.

In contrast, in Unix systems the libraries and executable are patched directly
and are available outside of the python environment as well.

### Beware of library load order

Beware if there are multiple dynamic libraries in other wheels or even on the
system with the same `SONAME`/`SOVERSION` (usually just the library file name).
Depending on the order of python or other script execution, the other libraries
(not the ones that were patched to be linked to) may be loaded first, and when
your libraries are loaded, the dependencies that have already been loaded will
be used instead of the ones that were patched to be linked to.

If you want to avoid this, consider using the [wheel repair tools] which always
bundle and mangle the libraries appropriately to preserve the consistency.
However, this also makes it impossible to link/fallback to system libraries or
link to a shared library in a different wheel.

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
[wheel repair tools]: #wheel-repair-tools

<!-- prettier-ignore-end -->
