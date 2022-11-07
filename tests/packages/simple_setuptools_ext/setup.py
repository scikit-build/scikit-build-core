from setuptools import setup

setup(
    name="cmake-example",
    version="0.0.1",
    cmake_source_dir=".",
    zip_safe=False,
    extras_require={"test": ["pytest>=6.0"]},
    python_requires=">=3.7",
)
