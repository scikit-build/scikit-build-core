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
from importlib.resources import files

try:
    from ._version import __version__
except ImportError:
    __version__ = None

def get_static_data():
    return files().joinpath("static_data").read_text().rstrip()

# Access importlib resources as early as possible in the import process to check
# for edge cases with import hooks.
static_data = get_static_data()

# Check consistency of various access modes (or describe unsupported access modes).
assert files("cmake_generated").joinpath("static_data").read_text().rstrip() == static_data

def get_namespace_static_data():
    # Ref https://github.com/python/importlib_resources/issues/262
    return files().joinpath("namespace1").joinpath("static_data").read_text().rstrip()
