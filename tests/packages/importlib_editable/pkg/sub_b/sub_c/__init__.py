# ruff: noqa: I001, F401
# mypy: ignore-errors

from .pmod_d import square as psquare_d
from .emod_d import square as esquare_d

# Level one import cousin
from .. import sub_d
from ..sub_d.pmod_e import square as psquare_e
from ..sub_d.emod_e import square as esquare_e
