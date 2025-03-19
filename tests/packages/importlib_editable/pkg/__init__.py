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
from . import sub_a

# Level two pure modules
from .sub_a import pmod_b

# Level two extension modules
from .sub_a import emod_b

# Level two subpackages
from .sub_b import sub_c

# Level three pure modules
from .sub_b.sub_c import pmod_d

# Level three extension modules
from .sub_b.sub_c import emod_d

__all__ = [
    "emod",
    "emod_a",
    "emod_b",
    "emod_d",
    "pmod",
    "pmod_a",
    "pmod_b",
    "pmod_d",
    "sub_a",
    "sub_c",
]
