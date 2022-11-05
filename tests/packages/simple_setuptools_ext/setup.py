from setuptools import setup

from scikit_build_core.setuptools.extension import CMakeExtension

setup(
    name="cmake-example",
    version="0.0.1",
    cmake_extensions=[
        CMakeExtension("cmake_example", define_macros=[("EXAMPLE_INFO", "42")])
    ],
    zip_safe=False,
    extras_require={"test": ["pytest>=6.0"]},
    python_requires=">=3.7",
)
