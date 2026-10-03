"""Exact internal amounts: 10,000 integer parts per internal unit.

Existing settlement paths still round each award/spend to cents. Historical
four-place click statistics and exchange rates retain four places. Decimal
HALF_EVEN is explicit; conversion always starts from the decimal text of a
legacy float, never its binary expansion. These are liabilities, not the
sender account's Telegram Stars.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN

from sqlalchemy import Numeric, cast
from sqlalchemy.ext.hybrid import hybrid_property

SCALE = 10_000
MAX_UNITS = 2**63 - 1


def decimal_amount(value: Decimal | str | int | float) -> Decimal:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("invalid money amount") from exc
    if not amount.is_finite():
        raise ValueError("money amount must be finite")
    return amount


def to_units(value: Decimal | str | int | float, *, places: int = 4) -> int:
    if places not in range(5):
        raise ValueError("money precision must be between zero and four places")
    amount = decimal_amount(value)
    if amount.copy_abs() > Decimal(MAX_UNITS) / SCALE + 1:
        raise ValueError("money amount exceeds signed 64-bit storage")
    amount = amount.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
    result = int(amount * SCALE)
    if abs(result) > MAX_UNITS:
        raise ValueError("money amount exceeds signed 64-bit storage")
    return result


def settlement_units(value: Decimal | str | int | float) -> int:
    return to_units(value, places=2)


def from_units(value: int) -> Decimal:
    return Decimal(value) / SCALE


def money_property(column: str, *, nullable: bool = False):
    """Compatibility accessor; all writes persist only the integer column."""
    def getter(self):
        units = getattr(self, column)
        return None if nullable and units is None else from_units(units or 0)

    def setter(self, value):
        units = None if nullable and value is None else to_units(value)
        if units is not None and units < 0:
            raise ValueError("persisted monetary amounts must be nonnegative")
        setattr(self, column, units)

    def expression(cls):
        return cast(getattr(cls, column), Numeric(24, 4)) / SCALE

    def update_expression(cls, value):
        # Literal setters in old administration/repositories remain supported.
        # Arithmetic paths must use *_units and cannot silently use SQL floats.
        return [(getattr(cls, column), None if nullable and value is None else to_units(value))]

    return hybrid_property(getter, setter, expr=expression, update_expr=update_expression)
