# Search paths

Scikit-build-core populates CMake search paths to take into account any other
CMake project installed in the same environment. In order to take advantage of
this the dependent project must populate a `cmake.*` entry-point.

## `<PackageName>_ROOT`

This is the recommended interface to be used for importing dependent packages
using `find_package`. This variable is populated by the dependent project's
entry-point `cmake.root`.

To configure the `cmake.root` entry-point to export to other projects, you can
use the CMake standard install paths in you `CMakeLists.txt` if you use
`wheel.install-dir` option, e.g.

```{code-block} cmake
:caption: CMakeLists.txt
:emphasize-lines: 14-16

include(CMakePackageConfigHelpers)
include(GNUInstallDirs)
write_basic_package_version_file(
    MyProjectConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)
configure_package_config_file(
    cmake/MyProjectConfig.cmake.in
    MyProjectConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/MyProject
)
install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/MyProjectConfigVersion.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/MyProjectConfig.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/MyProject
)
```

```{code-block} toml
:caption: pyproject.toml
:emphasize-lines: 2,5

[tool.scikit-build]
wheel.install-dir = "myproject"

[project.entry-points."cmake.root"]
MyProject = "myproject"
```

With this any consuming project that depends on this would automatically work
with `find_package(MyProject)` as long as it is in the `build-system.requires`
list.

````{tab} pyproject.toml

```toml
[tool.scikit-build.search]
ignore_entry_point = ["MyProject"]
[tool.scikit-build.search.roots]
OtherProject = "/path/to/other_project"
```

````

`````{tab} config-settings


````{tab} pip

```console
$ pip install . -v --config-settings=search.ignore_entry_point="MyProject" --config-settings=search.roots.OtherProject="/path/to/other_project"
```

````

````{tab} build

```console
$ pipx run build --wheel -Csearch.ignore_entry_point="MyProject" -Csearch.roots.OtherProject="/path/to/other_project"
```

````

````{tab} cibuildwheel

```toml
[tool.cibuildwheel.config-settings]
"search.ignore_entry_point" = ["MyProject"]
"search.roots.OtherProject" = "/path/to/other_project"
```

````

`````

````{tab} Environment


```yaml
SKBUILD_SEARCH_IGNORE_ENTRY_POINT: "MyProject"
SKBUILD_SEARCH_ROOTS_OtherProject: "/path/to/other_project"
```

````

## `CMAKE_PREFIX_PATH`

Another common search path that scikit-build-core populates is the
`CMAKE_PREFIX_PATH` which is a common catch-all for all CMake search paths, e.g.
`find_package`, `find_program`, `find_path`. This is populated by default with
the `site-packages` folder where the project will be installed or the build
isolation's `site-packages` folder. This default can be disabled by setting

```toml
[tool.scikit-build]
search.site-packages = false
```

Additionally, scikit-build-core reads the entry-point `cmake.prefix` of the
dependent projects, which is similarly export as

```toml
[project.entry-points."cmake.prefix"]
MyProject = "myproject"
```

````{tab} pyproject.toml

```toml
[tool.scikit-build.search]
ignore_entry_point = ["MyProject"]
prefixes = ["/path/to/prefixA", "/path/to/prefixB"]
```

````

`````{tab} config-settings


````{tab} pip

```console
$ pip install . -v --config-settings=search.ignore_entry_point="MyProject" --config-settings=search.prefixes="/path/to/prefixA;/path/to/prefixB"
```

````

````{tab} build

```console
$ pipx run build --wheel -Csearch.ignore_entry_point="MyProject" -Csearch.prefixes="/path/to/prefixA;/path/to/prefixB"
```

````

````{tab} cibuildwheel

```toml
[tool.cibuildwheel.config-settings]
"search.ignore_entry_point" = ["MyProject"]
"search.prefixes" = ["/path/to/prefixA", "/path/to/prefixB"]
```

````

`````

````{tab} Environment


```yaml
SKBUILD_SEARCH_IGNORE_ENTRY_POINT: "MyProject"
SKBUILD_SEARCH_PREFIXES: "/path/to/prefixA;/path/to/prefixB"
```

````

## `CMAKE_MODULE_PATH`

Scikit-build-core also populates `CMAKE_MODULE_PATH` variable used to search for
CMake modules using the `include()` command (if the `.cmake` suffix is omitted).

[`CMAKE_PREFIX_PATH`]: #cmake-prefix-path
