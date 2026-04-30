from decimal import Decimal
from gaming_research.exhaustion.spec import GridSpec

TINY_SPEC = GridSpec(
    min1_values  = (Decimal("2"),),
    min2_values  = (Decimal("1"),),
    span1        = Decimal("15"),
    span2        = Decimal("15"),
    a1           = Decimal("0.5"),
    a2           = Decimal("0.5"),
    p_values     = (Decimal("0.5"),),
    c1_min       = Decimal("0.1"),
    c1_max       = Decimal("24"),
    c1_step      = Decimal("0.1"),
    c2_min       = Decimal("0.1"),
    c2_max       = Decimal("24"),
    c2_step      = Decimal("0.1"),
    avg_diff_min = Decimal("1"),
)
