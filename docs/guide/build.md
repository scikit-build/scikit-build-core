# Build procedure

## Quickstart

For any backend, you can make a SDist and then build a wheel from it with one
command (choose your favorite way to run apps):

````{tab} pipx

```bash
pipx run build
```

````

````{tab} uv

```bash
uv build
```

````

````{tab} pip

```bash
pip install build
python -m build
```

````

You can then check the file contents:

```bash
tar -tf dist/*.tar.gz
unzip -l dist/*.whl
```

The SDist should contain a copy of the repo with all the files you'll need (CI
files and such are not required). And the wheel should look like the installed
project with a few helper files.

You can inspect any SDist or wheel on PyPI at <https://inspector.pypi.io>.

## In-depth

SDists and wheels are produced by the same hook sequence. Building either one
(`pipx run build --sdist` or `--wheel`):

1. Reads `pyproject.toml` to get the `build-system` table.
2. Sets up a new isolated environment with the packages listed in
   `build-system.requires`.
3. Runs `.get_requires_for_build_sdist(...)` or
   `.get_requires_for_build_wheel(...)` inside the module listed in
   `build-system.build-backend`, if it exists. If this returns a list, all the
   packages requested are installed. This allows a backend to dynamically
   declare dependencies.
4. Runs `.build_sdist(...)` or `.build_wheel(...)` inside the module listed in
   `build-system.build-backend`. The backend produces the file and returns the
   filename.

Details of the arguments are skipped above, but they allow arbitrary settings
(called config-settings) to be passed to all the hook functions and handle
directories. If you turn off isolated environment building (`--no-isolation` in
`build` or `--no-build-isolation` in `pip`), then steps 2 and 3 are skipped.

There are a few other hooks as well; one to allow metadata to be produced
without building a wheel, and editable versions of the wheel build. Editable
"wheels" are temporary wheels that are only produced to immediately install and
discard, and are expected to provide mechanisms to link back to the source code.

:::{note}

If you run build without arguments, it will build an SDist first, then will
build a wheel from the SDist. This will error if you do not have a valid SDist.
If you pass `--sdist --wheel`, it will build both directly from the source
instead. Note that pip cannot build SDists.

:::

### SDist

The SDist is a tarfile with all the code required to build the project, along
with a little bit of metadata (a `PKG-INFO` file).

Without build isolation, you can build an SDist manually with
`python -c "from scikit_build_core.build import build_sdist; build_sdist('dist')"`.
This will produce an SDist in the `dist` directory. For any other backend,
substitute the backend above.

Since you can build a wheel from the source or from the SDist, the structure
should be identical to the source, though some files (like CI files) may be
omitted. Files from git submodules should be included. It is best if the SDist
can be installed without internet connection, but that's not always the case.

### Wheel

The wheel is a zip file (ending in `.whl`) with the built code of the project,
along with required metadata. There is no code that executes on install; it is a
simple unpack with a few rules about directories. Wheels do not contain
`pyproject.toml` or other configuration files.

#### File structure in the wheel

The basic structure of the wheel is what will be extracted to site-packages.
This means most of the files are usually in `<package-name>/...`, though if a
top-level extension is present, then that could be something like
`<package-name>.<platform-tag>.so`. There's also a
`<package-name>-<package-version>.dist-info/` directory with various metadata
files in it (`METADATA`, `WHEEL`, and `RECORD`), along with license files. There
are a few other metadata files that could be here too, like `entry_points.txt`.

There are also several directories that installers can extract to different
locations, namely:

- `<package-name>.data/scripts`: Goes to the `/bin` or `/Scripts` directory in
  the environment. Any file starting with `#!python` will get the correct path
  injected by the installer. Most build-backends (like setuptools and
  scikit-build-core) will convert normal Python shabang lines like
  `#!/usr/bin/env python` into `#!python` for you. Though if you are writing
  Python and placing them here, it's usually better to use entry points and let
  the installer generate the entire file.
- `<package-name>.data/headers`: Goes to the include directory for the current
  version of Python in the environment.
- `<package-name>.data/data`: Goes to the root of the environment.

Note that if a user is not in a virtual environment, these folders install
directly to the Python install's location, which could be `/` or `/usr`! In
general, it's best to put data inside the package's folder in site-packages and
then use `importlib.resources` to access it.

### Installing

Installing simply unpacks a wheel into the target filesystem. No code is run, no
configuration files are present. If pip tries to install a repo or an SDist, it
will first build a wheel[^1] as shown above, then install that. `installer` is a
standalone tool that is designed entirely to install wheels.

If you want to run code on install, you either have to use an SDist, or depend
on a package that is SDist only. However, this is quite rarely required.

## Binary wheels and distributing

A wheel filename has several components:

```
scikit_build_core-0.1.2-py3-none-any.whl
|_______________| |___| |_| |__| |_|
         |          |    |    |    \
       name      version |    |  platform
                      python  |
                             abi
```

The three new items here (compared to SDists) are the [compatibility tags][]:

- `python tag`: The first version of Python the wheel is compatible with. Often
  `py3` for pure Python wheels, or `cp312` (etc) for compiled wheels.
- `abi tag`: The interpreter ABI this was built for. `none` for pure Python
  wheels or compiled wheels that don't use the Python API, `abi3` for stable ABI
  / limited API wheels, `abi3t` for free-threaded stable ABI wheels, and `cp312`
  (etc) for normal compiled wheels.
- `platform tag`: This is the platform the wheel is valid on, such as `any`,
  `linux_x86_64`, or `manylinux_2_17_x86_64`.

```{versionadded} 1.0
The `abi3t` tag for free-threaded stable ABI wheels.
```

(repairing-wheels)=

## Repairing

The wheels produced by default are not designed to be redistributable. Making
them redistributable depends on platform:

| Platform | Repair tool    | Notes                                                                                                                                                         |
| -------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Linux    | [auditwheel][] | `linux_*` tags can't go to PyPI; build in a restricted environment (like the manylinux images) so the repaired wheel earns a `manylinux_*`/`musllinux_*` tag. |
| macOS    | [delocate][]   | Build with the official CPython releases and a reasonable `MACOSX_DEPLOYMENT_TARGET` (10.9+); (carefully) cross compile for Apple Silicon or use `macos-14`+. |
| Windows  | [delvewheel][] | Only needed if you bundle dependencies; younger than the others and uses a few more intrusive workarounds.                                                    |

Repair tools verify you only use allowed system libraries and bundle external
libraries into the wheel with mangled symbols to avoid conflicts.

The easiest way to handle all the above for all Python versions, OSs,
architectures, including testing, is to use [cibuildwheel][]. There's also a
fairly new tool, [repairwheel][], that combines all these tools. Tools usually
allow extra flags that can be used for trickier repairs, like ignoring CUDA
libraries when bundling (which technically is not a true manylinux wheel, but is
the current workaround).

<!-- prettier-ignore-start -->

[^1]: If no `pyproject.toml` is present, pip and build fall back on legacy
      `setup.py`-based builds; using scikit-build-core avoids this entirely.

[auditwheel]: https://github.com/pypa/auditwheel
[delocate]: https://github.com/matthew-brett/delocate
[delvewheel]: https://github.com/adang1345/delvewheel
[repairwheel]: https://github.com/jvolkman/repairwheel
[cibuildwheel]: https://cibuildwheel.pypa.io
[compatibility tags]: https://packaging.python.org/en/latest/specifications/binary-distribution-format

<!-- prettier-ignore-end -->
