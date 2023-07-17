# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import importlib
import inspect
import os
import sys
import warnings
from pathlib import Path

if sys.version_info < (3, 8):
    import importlib_metadata
else:
    import importlib.metadata as importlib_metadata

try:
    import scikit_build_core
except ModuleNotFoundError:
    scikit_build_core = None

ROOT = Path(__file__).parent.parent.resolve()

# Custom extension
sys.path.append(str(ROOT / "docs/ext"))

try:
    from scikit_build_core import __version__ as version
except ModuleNotFoundError:
    try:
        version = importlib_metadata.version("scikit-build-core")
    except ModuleNotFoundError:
        msg = (
            "Package should be installed to produce documentation! "
            "Assuming a modern git archive was used for version discovery."
        )
        warnings.warn(msg, stacklevel=1)

        from setuptools_scm import get_version

        version = get_version(root=ROOT, fallback_root=ROOT)

# Filter git details from version
release = version.split("+")[0]


# -- Project information -----------------------------------------------------

project = "scikit-build-core"
copyright = "2022, The Scikit-Build admins"
author = "Henry Schreiner"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.linkcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "conftabs",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = []

source_suffix = [".rst", ".md"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "**.ipynb_checkpoints",
    "Thumbs.db",
    ".DS_Store",
    ".env",
    ".venv",
    "examples/downstream",
]


intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "packaging": ("https://packaging.pypa.io/en/stable", None),
    "setuptools": ("https://setuptools.pypa.io/en/latest", None),
    "pyproject_metadata": ("https://pep621.readthedocs.io/en/latest", None),
}

nitpick_ignore = [
    ("py:class", "setuptools.dist.Distribution"),
    ("py:class", "T"),
    ("py:class", "scikit_build_core.settings.sources.T"),
]

linkcheck_anchors_ignore = [
    # This seems to be broken on GitHub readmes
    "default-versioning-scheme",
    "git-archives",
]
# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"


# -- Extension configuration -------------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "substitution",
    "deflist",
]


myst_substitutions = {
    "version": version,
}

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section)

man_pages = [
    (
        "man",
        project,
        "A Python module build backend for CMake",
        [author],
        7,
    )
]


commit = os.environ.get("READTHEDOCS_GIT_COMMIT_HASH", "main")
code_url = "https://github.com/scikit-build/scikit-build-core/blob"


def linkcode_resolve(domain: str, info: dict[str, str]) -> str | None:
    if scikit_build_core is None:
        return None

    if domain != "py":
        return None

    mod = importlib.import_module(info["module"])
    if "." in info["fullname"]:
        objname, attrname = info["fullname"].split(".")
        obj = getattr(mod, objname)
        try:
            # object is a method of a class
            obj = getattr(obj, attrname)
        except AttributeError:
            # object is an attribute of a class
            return None
    else:
        obj = getattr(mod, info["fullname"])

    try:
        file = Path(inspect.getsourcefile(obj))
        lines = inspect.getsourcelines(obj)
    except TypeError:
        # e.g. object is a typing.Union
        return None
    try:
        mod = Path(inspect.getsourcefile(scikit_build_core)).parent
        file = file.relative_to(mod)
    except ValueError:
        return None
    start, end = lines[1], lines[1] + len(lines[0]) - 1

    return f"{code_url}/{commit}/src/scikit_build_core/{file}#L{start}-L{end}"
