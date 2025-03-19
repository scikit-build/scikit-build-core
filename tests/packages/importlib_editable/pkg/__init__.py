# Don't let ruff sort imports in this file, we want to keep them with the comments as is
# for clarity.
# ruff: noqa: I001
# mypy: ignore-errors

# Level zero import global modules
import emod
import pmod

# Level one pure modules
from . import pmod_a

# Level one extension modules
from . import emod_a

# Level one subpackages
from . import sub_a, sub_b

# Level two pure modules
from .sub_a import pmod_b
from .sub_b import pmod_c

# Level two extension modules
from .sub_a import emod_b
from .sub_b import emod_c

# Level two subpackages
from .sub_b import sub_c, sub_d

# Level three pure modules
from .sub_b.sub_c import pmod_d
from .sub_b.sub_d import pmod_e

# Level three extension modules
from .sub_b.sub_c import emod_d
from .sub_b.sub_d import emod_e

__all__ = [
    "emod",
    "emod_a",
    "emod_b",
    "emod_c",
    "emod_d",
    "emod_e",
    "pmod",
    "pmod_a",
    "pmod_b",
    "pmod_c",
    "pmod_d",
    "pmod_e",
    "sub_a",
    "sub_b",
    "sub_c",
    "sub_d",
]
