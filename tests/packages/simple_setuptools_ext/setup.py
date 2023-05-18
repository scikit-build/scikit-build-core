from setuptools import find_packages, setup

setup(
    name="cmake-example",
    version="0.0.1",
    cmake_source_dir=".",
    zip_safe=False,
    package_dir={"": "src"},
    packages=find_packages(),
    extras_require={"test": ["pytest>=6.0"]},
    python_requires=">=3.7",
    license_files=["LICENSE"],
)
