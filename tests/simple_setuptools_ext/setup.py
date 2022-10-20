from setuptools import setup

from scikit_build_core.setuptools.extension import CMakeBuild, CMakeExtension

setup(
    name="cmake-example",
    version="0.0.1",
    ext_modules=[
        CMakeExtension("cmake_example", define_macros=[("EXAMPLE_INFO", "42")])
    ],
    zip_safe=False,
    extras_require={"test": ["pytest>=6.0"]},
    cmdclass={"build_ext": CMakeBuild},
    python_requires=">=3.7",
)
