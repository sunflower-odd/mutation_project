
"""billing package – public façade over billing.calculator"""
from importlib import metadata as _metadata
from .calculator import (
    price_with_tax, apply_coupon, compute_total, booking_fee,
    compute_subtotal, convert_currency, validate_coupon, split_payment, parse_iso_date, compute_refund, bulk_discount,
    compute_bulk_total, tax_breakdown, validate_tax_number, tax_breakdown, validate_tax_number, apply_dynamic_tax,
    loyalty_points_earned, apply_loyalty_discount, cap_price, round_money, is_weekend_rate
)

__all__ = [
    "price_with_tax", "apply_coupon", "compute_total", "booking_fee",
"compute_subtotal", "convert_currency", "validate_coupon",
"split_payment", "parse_iso_date", "compute_refund", "bulk_discount",
"compute_bulk_total", "tax_breakdown", "validate_tax_number",
"apply_dynamic_tax", "loyalty_points_earned",
"apply_loyalty_discount", "cap_price", "round_money",
"is_weekend_rate"
]

try:
    __version__ = _metadata.version(__name__)
except _metadata.PackageNotFoundError:
    __version__ = "0.1.0"
