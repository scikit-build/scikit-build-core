import sys

if sys.version_info < (3, 9):
    from importlib_resources import files
else:
    from importlib.resources import files

from .c_module import c_method


def call_c_method():
    print(c_method())


def py_method():
    print("py_method")


def read_py_data_txt():
    root = files("shared_pkg.data")
    py_data = root / "py_data.txt"
    print(py_data.read_text())


def read_c_generated_txt():
    root = files("shared_pkg.data")
    c_generated_txt = root / "c_generated.txt"
    print(c_generated_txt.read_text())
