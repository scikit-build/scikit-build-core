# ruff: noqa: I001, F401
# mypy: ignore-errors

from .pmod_b import square as psquare
from .emod_b import square as esquare

# Level one import cousin
from .. import sub_b
from ..sub_b.pmod_c import square as psquare_c
from ..sub_b.emod_c import square as esquare_c

# Level one import distant cousin
from ..sub_b import sub_c
from ..sub_b.sub_c.pmod_d import square as psquare_d
from ..sub_b.sub_c.emod_d import square as esquare_d
