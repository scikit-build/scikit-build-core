# Debugging and IDE integration

Coverage tools (`gcov`/`gcovr`), debuggers (GDB), and editor tooling (the VSCode
C/C++ extension, clangd) all depend on paths recorded at compile time. Two
scikit-build-core defaults make those paths disappear:

- **The build directory is temporary.** Without {confval}`build-dir` set,
  scikit-build-core builds in a temporary directory that is deleted after the
  build — taking coverage data, debug artifacts, and `compile_commands.json`
  with it.
- **Build isolation hides everything else.** `pip install .`, `python -m build`,
  `uv build`, and `uv sync` copy your project and install the build dependencies
  into throwaway environments, so recorded source paths and include paths no
  longer exist after the build.

The shared fix is a persistent build directory with isolation disabled (after
preinstalling your build dependencies), so everything stays in place:

```bash
pip install --no-build-isolation -Cbuild-dir=build -ve .
```

You can set the build directory in `pyproject.toml` instead of on the command
line:

```toml
[tool.scikit-build]
build-dir = "build"
```

## Coverage and debugging (gcov / gcovr / GDB)

gcov records the source path and compilation directory in the `.gcno`
(compile-time) and `.gcda` (run-time) files, and DWARF debug info records the
source path in the compiled extension. If those paths no longer exist when you
run the tool, you get errors such as

```console
$ gcovr --xml coverage.xml -r .
(ERROR) Trouble processing '.../CMakeFiles/foo.dir/_foo.c.gcda' with working directory '/home'.
```

or GDB that cannot show source lines even with debug flags enabled.

With the persistent-tree install above, run gcovr against the persistent tree,
pointing the root at your source:

```bash
gcovr -r . build
```

If you would rather not depend on the paths staying put, make the recorded paths
relocatable with compiler flags — `-fprofile-abs-path` for gcov and
`-ffile-prefix-map=<build>=<src>` (or `-fdebug-prefix-map=...` for debug info
only) — for example via {confval}`cmake.define` or `CFLAGS`.

(compile-commands)=

## IDE IntelliSense (`compile_commands.json`)

Editor tooling resolves headers like `pybind11/pybind11.h` from your include
paths. With build isolation, binding libraries such as pybind11 and nanobind
live in a throwaway overlay — CMake reports a path such as
`.../Temp/pip-build-env-xxxx/overlay/Lib/site-packages/pybind11/include`, which
no longer exists when your editor looks for it.

Extend the shared fix by having CMake export a compile database:

````{tab} pip

```bash
pip install scikit-build-core pybind11
pip install --no-build-isolation --check-build-dependencies -ve . \
  -Cbuild-dir=build \
  -Ccmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=1
```

````

````{tab} uv

```bash
uv pip install scikit-build-core pybind11
uv pip install --no-build-isolation -ve . \
  -Cbuild-dir=build \
  -Ccmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=1
```

In a uv-managed project, disable isolation for your package instead, so
`uv sync` reuses the environment's build dependencies rather than a discarded
overlay:

```toml
[tool.uv]
no-build-isolation-package = ["mypackage"]
```

````

This writes `build/compile_commands.json` with real, persistent paths. Then
point your editor at the file. For clangd, add `--compile-commands-dir=build`
(or a `.clangd` with a `CompileFlags.CompilationDatabase: build` entry); for the
VSCode C/C++ extension, set
`"C_Cpp.default.compileCommands": "${workspaceFolder}/build/compile_commands.json"`.
See [editable installs](../configuration/editable.md) for the related
`--no-build-isolation` recommendations.
