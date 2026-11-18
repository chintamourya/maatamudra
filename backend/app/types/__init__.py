from .base import TypeDef
from .employment import EMPLOYMENT_TYPE
from .freelance import FREELANCE_TYPE
from .rental import RENTAL_TYPE
from .common import COMMON_TYPES

REGISTRY: dict[str, TypeDef] = {
    t.key: t for t in (RENTAL_TYPE, FREELANCE_TYPE, EMPLOYMENT_TYPE, *COMMON_TYPES)
}
