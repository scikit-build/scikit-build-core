import os

from setuptools import Distribution, Extension

from scikit_build_core.setuptools.wrapper import setup


def cmake_install_dir():
    # The path classic scikit-build's skbuild.constants.CMAKE_INSTALL_DIR()
    # compat shim predicts; projects like DracoPy compile plain Extensions
    # against files CMake installed here.
    build_ext = Distribution().get_command_obj("build_ext")
    build_ext.ensure_finalized()
    return os.path.join(build_ext.build_temp, "_skbuild", "cmake-install")


setup(
    name="wrapper-staged-install",
    version="0.0.1",
    cmake_source_dir=".",
    ext_modules=[
        Extension(
            "staged_install_example",
            sources=[os.path.join("src", "module.c")],
            include_dirs=[os.path.join(cmake_install_dir(), "include")],
        )
    ],
    zip_safe=False,
    python_requires=">=3.8",
)
