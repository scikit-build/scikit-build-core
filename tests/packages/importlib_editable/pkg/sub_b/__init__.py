# Don't let ruff sort imports in this file, we want to keep them with the comments as is
# for clarity.
# ruff: noqa: I001, F401
# mypy: ignore-errors

# Level one pure modules
from .pmod_c import square as psquare_c

# Level one extension modules
from .emod_c import square as esquare_c

# Level one subpackages
from . import sub_c

# Level two pure modules
from .sub_c.pmod_d import square as psquare_d

# Level two extension modules
from .sub_c.emod_d import square as esquare_d
