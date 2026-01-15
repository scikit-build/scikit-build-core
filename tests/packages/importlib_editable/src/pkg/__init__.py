# Don't let ruff sort imports in this file, we want to keep them with the comments as is
# for clarity.
# ruff: noqa: I001, F401
# mypy: ignore-errors

# Level zero import global modules
from pmod import square as psquare
from emod import square as esquare

# Level one pure modules
from .pmod_a import square as psquare_a

# Level one extension modules
from .emod_a import square as esquare_a

# Level one subpackages
from . import sub_a

# Level two pure modules
from .sub_a.pmod_b import square as psquare_b

# Level two extension modules
from .sub_a.emod_b import square as esquare_b

# Level two subpackages
from .sub_b import sub_c

# Level three pure modules
from .sub_b.sub_c.pmod_d import square as psquare_d

# Level three extension modules
from .sub_b.sub_c.emod_d import square as esquare_d
