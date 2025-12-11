"""Package that includes several non-Python non-module files.

Support some test cases aimed at testing our ability to find generated files
and static package data files in editable installations.

We are exercising the importlib machinery to find files that
are generated in different phases of the build and in different parts of
the package layout to check that the redirection works correctly in an
editable installation.

The test package includes raw data files and shared object libraries that
are accessed via `ctypes`.

We test files (generated and static)

* at the top level of the package,
* in subpackages, and
* in a namespace package.

We test access

* from modules at the same level as the files,
* one level above and below, and
* from parallel subpackages.

Question: Do we want to test both relative and absolute imports or just one or the other?
"""

import ctypes
import sys
from importlib.resources import as_file, files, read_text

try:
    from ._version import __version__
except ImportError:
    __version__ = None


def get_static_data():
    return read_text("cmake_generated", "static_data").rstrip()


def get_configured_data():
    return files().joinpath("configured_file").read_text().rstrip()


def get_namespace_static_data():
    # read_text is able to handle a namespace subpackage directly, though `files()` is not.
    return read_text("cmake_generated.namespace1", "static_data").rstrip()


def get_namespace_generated_data():
    # Note that `files("cmake_generated.namespace1")` doesn't work.
    # Ref https://github.com/python/importlib_resources/issues/262
    return (
        files().joinpath("namespace1").joinpath("generated_data").read_text().rstrip()
    )


def ctypes_function():
    # Question: can anyone think of a clever way to embed the actual library name in some other package metadata?
    if sys.platform == "win32":
        lib_suffix = "dll"
    else:
        lib_suffix = "so"
    with as_file(files().joinpath(f"pkg.{lib_suffix}")) as lib_path:
        lib = ctypes.cdll.LoadLibrary(str(lib_path))
        return lib.func
