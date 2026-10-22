from decimal import Decimal
from fractions import Fraction

from django import template

register = template.Library()


@register.filter
def decimal_display(value):
    """Show a decimal beside the engine's exact fraction, e.g. "57/2" ->
    "28.5 (57/2)". Display only: the stored string is never changed.
    """
    if not value:
        return ""
    text = str(value)
    if "/" not in text:
        return text
    # A qualified statistic ("<31/3") keeps its qualifier on the decimal.
    qualifier = "<" if text.startswith("<") else ""
    try:
        fraction = Fraction(text.removeprefix(qualifier))
    except (ValueError, ZeroDivisionError):
        return text
    decimal = Decimal(fraction.numerator) / Decimal(fraction.denominator)
    shown = format(decimal.quantize(Decimal("0.0001")).normalize(), "f")
    exact = Fraction(shown) == fraction
    shown = qualifier + shown
    return f"{shown} ({text})" if exact else f"≈ {shown} ({text})"
