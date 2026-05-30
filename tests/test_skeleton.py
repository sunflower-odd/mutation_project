import pytest
from datetime import datetime
from billing.calculator import (
    price_with_tax, apply_coupon, compute_subtotal, booking_fee,
    compute_total, validate_coupon, split_payment, convert_currency,
    parse_iso_date, compute_refund, bulk_discount, compute_bulk_total,
    tax_breakdown, validate_tax_number, apply_dynamic_tax,
    loyalty_points_earned, apply_loyalty_discount, cap_price,
    round_money, is_weekend_rate, _round, TAX_RATE, BOOKING_FEE_PER_TICKET
)

class TestPriceWithTax:
    def test_negative_raises_value_error(self):
        with pytest.raises(ValueError):
            price_with_tax(-0.01)
        with pytest.raises(ValueError):
            price_with_tax(-100)

    def test_zero_returns_zero(self):
        assert price_with_tax(0) == 0

    def test_positive_values(self):
        assert price_with_tax(100) == 121.0
        assert price_with_tax(50) == 60.5
        assert price_with_tax(0.01) == 0.01
        assert price_with_tax(0.99) == 1.2
        assert price_with_tax(33.33) == 40.33

    def test_rounding_edge_cases(self):
        assert price_with_tax(0.8264) == 1.0
        assert price_with_tax(0.8265) == 1.0


class TestApplyCoupon:
    def test_invalid_coupon(self):
        assert apply_coupon(100, "COUPON") == 100
        assert apply_coupon(100, "") == 100

    def test_none_coupon(self):
        assert apply_coupon(100, None) == 100

    def test_valid_coupons_case_insensitive(self):
        assert apply_coupon(100, "SPORT10") == 90
        assert apply_coupon(100, "sport10") == 90
        assert apply_coupon(100, "SpOrT10") == 90

    def test_all_coupon_codes(self):
        assert apply_coupon(100, "SPORT10") == 90
        assert apply_coupon(100, "NEWUSER5") == 95
        assert apply_coupon(100, "BLACKFRIDAY") == 75

    def test_rounding_with_coupon(self):
        assert apply_coupon(99.99, "SPORT10") == 89.99

    def test_zero_gross(self):
        assert apply_coupon(0, "SPORT10") == 0

    def test_edge_cases(self):
        assert apply_coupon(0.01, "SPORT10") == 0.01


class TestComputeSubtotal:
    def test_positive_qty(self):
        assert compute_subtotal(10.5, 3) == 31.5
        assert compute_subtotal(0.01, 1) == 0.01
        assert compute_subtotal(0.01, 100) == 1.0

    def test_large_numbers(self):
        assert compute_subtotal(0.01, 10000) == 100.0

    def test_rounding_precision(self):
        assert compute_subtotal(0.1, 3) == 0.3
        assert compute_subtotal(0.33, 3) == 0.99
        assert compute_subtotal(1.999, 2) == 4.0

    def test_zero_qty_raises(self):
        with pytest.raises(ValueError):
            compute_subtotal(10, 0)

    def test_negative_qty_raises(self):
        with pytest.raises(ValueError):
            compute_subtotal(10, -1)
        with pytest.raises(ValueError):
            compute_subtotal(10, -100)

    def test_negative_price_allowed(self):
        assert compute_subtotal(-10, 2) == -20.0


class TestBookingFee:
    def test_single_ticket(self):
        assert booking_fee(1) == BOOKING_FEE_PER_TICKET

    def test_multiple_tickets(self):
        assert booking_fee(2) == 1.0
        assert booking_fee(5) == 2.5
        assert booking_fee(10) == 5.0

    def test_zero_tickets(self):
        assert booking_fee(0) == 0.0

    def test_negative_tickets(self):
        assert booking_fee(-1) == -0.5

    def test_rounding(self):
        assert booking_fee(3) == 1.5


class TestComputeTotal:
    def test_integration_no_coupon(self):
        unit_price = 10.0
        qty = 2
        subtotal = compute_subtotal(unit_price, qty)
        fee = booking_fee(qty)
        expected = price_with_tax(subtotal + fee)
        assert compute_total(unit_price, qty) == expected

    def test_integration_with_coupon(self):
        unit_price = 10.0
        qty = 2
        coupon = "SPORT10"
        subtotal = compute_subtotal(unit_price, qty)
        fee = booking_fee(qty)
        gross = price_with_tax(subtotal + fee)
        expected = apply_coupon(gross, coupon)
        assert compute_total(unit_price, qty, coupon) == expected

    def test_edge_cases(self):
        assert compute_total(0.01, 1) == price_with_tax(0.01 + booking_fee(1))
        assert compute_total(100, 1000, "BLACKFRIDAY")

    def test_zero_qty_should_raise(self):
        with pytest.raises(ValueError):
            compute_total(10, 0)


class TestValidateCoupon:
    def test_valid_coupons_case_insensitive(self):
        assert validate_coupon("SPORT10") is True
        assert validate_coupon("sport10") is True
        assert validate_coupon("NEWUSER5") is True
        assert validate_coupon("BLACKFRIDAY") is True

    def test_invalid_coupons(self):
        assert validate_coupon("") is False
        assert validate_coupon("SPORT") is False
        assert validate_coupon("SPORT100") is False
        assert validate_coupon("BLACK") is False

    def test_none_input_raises(self):
        with pytest.raises(AttributeError):
            validate_coupon(None)


class TestSplitPayment:
    def test_equal_split(self):
        assert split_payment(10, 2) == [5.0, 5.0]
        assert split_payment(100, 4) == [25.0, 25.0, 25.0, 25.0]

    def test_split_with_rounding(self):
        result = split_payment(10, 3)
        assert result == [3.33, 3.33, 3.34]
        assert sum(result) == 10.0

    def test_rounding_edge_cases(self):
        result = split_payment(0.01, 2)
        assert sum(result) == 0.01

        result = split_payment(0.03, 2)
        assert result == [0.02, 0.01]

    def test_single_part(self):
        assert split_payment(100, 1) == [100.0]

    def test_negative_parts_raises(self):
        with pytest.raises(ValueError):
            split_payment(100, -1)

    def test_zero_parts_raises(self):
        with pytest.raises(ValueError):
            split_payment(100, 0)

    def test_large_split(self):
        result = split_payment(1000, 100)
        assert len(result) == 100
        assert all(part == 10.0 for part in result)


class TestConvertCurrency:
    def test_eur_to_eur(self):
        assert convert_currency(100, "EUR") == 100
        assert convert_currency(100, "eur") == 100

    def test_eur_to_usd(self):
        assert convert_currency(100, "USD") == 108.70

    def test_eur_to_gbp(self):
        assert convert_currency(100, "GBP") == 86.96

    def test_rounding_precision(self):
        assert convert_currency(1, "USD") == 1.09
        assert convert_currency(0.01, "USD") == 0.01

    def test_invalid_currency_raises_key_error(self):
        with pytest.raises(KeyError):
            convert_currency(100, "JPY")
        with pytest.raises(KeyError):
            convert_currency(100, "")

    def test_zero_amount(self):
        assert convert_currency(0, "USD") == 0


class TestParseIsoDate:
    def test_valid_full_datetime(self):
        dt = parse_iso_date("2026-01-01T12:30:45")
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45

    def test_valid_date_only(self):
        dt = parse_iso_date("2026-12-25")
        assert dt.year == 2026
        assert dt.month == 12
        assert dt.day == 25
        assert dt.hour == 0

    def test_invalid_format_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_iso_date("2024/01/01")
        with pytest.raises(ValueError):
            parse_iso_date("some_date")
        with pytest.raises(ValueError):
            parse_iso_date("")

class TestComputeRefund:
    def test_zero_percentage(self):
        assert compute_refund(100, 0) == 0
        assert compute_refund(1000, 0) == 0

    def test_full_percentage(self):
        assert compute_refund(100, 1) == 100
        assert compute_refund(50.50, 1) == 50.50

    def test_partial_percentage(self):
        assert compute_refund(200, 0.25) == 50
        assert compute_refund(100, 0.33) == 33.0
        assert compute_refund(100, 0.5) == 50

    def test_rounding(self):
        assert compute_refund(100, 0.33) == 33.0
        assert compute_refund(99.99, 0.33) == 33.0

    def test_negative_percentage_raises(self):
        with pytest.raises(ValueError):
            compute_refund(100, -0.01)

    def test_percentage_above_one_raises(self):
        with pytest.raises(ValueError):
            compute_refund(100, 1.01)
        with pytest.raises(ValueError):
            compute_refund(100, 2)

    def test_zero_total(self):
        assert compute_refund(0, 0.5) == 0


class TestBulkDiscount:
    def test_no_discount_small_qty(self):
        for qty in range(1, 10):
            assert bulk_discount(qty) == 0.0

    def test_medium_discount(self):
        for qty in range(10, 20):
            assert bulk_discount(qty) == 0.08
        assert bulk_discount(10) == 0.08
        assert bulk_discount(19) == 0.08

    def test_large_discount(self):
        for qty in [20, 50, 100, 1000]:
            assert bulk_discount(qty) == 0.15

    def test_boundary_values(self):
        assert bulk_discount(9) == 0.0
        assert bulk_discount(10) == 0.08
        assert bulk_discount(19) == 0.08
        assert bulk_discount(20) == 0.15

    def test_zero_qty(self):
        assert bulk_discount(0) == 0.0


class TestComputeBulkTotal:
    def test_no_discount(self):
        result = compute_bulk_total(10, 5)
        expected = price_with_tax(compute_subtotal(10, 5))
        assert result == expected

    def test_medium_discount(self):
        result = compute_bulk_total(10, 10)
        subtotal_with_discount = _round(100 * (1 - 0.08))
        expected = price_with_tax(subtotal_with_discount)
        assert result == expected

    def test_large_discount(self):
        result = compute_bulk_total(10, 20)
        subtotal_with_discount = _round(200 * (1 - 0.15))
        expected = price_with_tax(subtotal_with_discount)
        assert result == expected

    def test_rounding_in_discount(self):
        result = compute_bulk_total(0.33, 10)
        assert result > 0

    def test_boundary_values(self):
        result9 = compute_bulk_total(10, 9)
        result10 = compute_bulk_total(10, 10)
        assert result9 != result10


class TestTaxBreakdown:
    def test_basic_breakdown(self):
        net, tax = tax_breakdown(100)
        assert net == 100
        assert tax == 21.0

    def test_tax_calculation_precision(self):
        net, tax = tax_breakdown(33.33)
        assert tax == 7.0

    def test_zero_net(self):
        net, tax = tax_breakdown(0)
        assert net == 0
        assert tax == 0

    def test_tax_rate_constant(self):
        assert tax_breakdown(100)[1] == 100 * TAX_RATE
        assert tax_breakdown(50)[1] == 50 * TAX_RATE


class TestValidateTaxNumber:
    def test_valid_lv_tax_numbers(self):
        assert validate_tax_number("LV1234567890") is True
        assert validate_tax_number("LV0000000000") is True

    def test_invalid_start(self):
        assert validate_tax_number("US1234567890") is False
        assert validate_tax_number("Lv1234567890") is False
        assert validate_tax_number("1234567890") is False

    def test_invalid_length(self):
        assert validate_tax_number("LV123") is False
        assert validate_tax_number("LV12345678901") is False
        assert validate_tax_number("LV123456789") is False

    def test_empty_string(self):
        assert validate_tax_number("") is False

    def test_case_sensitivity(self):
        assert validate_tax_number("lv1234567890") is False


class TestApplyDynamicTax:
    def test_lv_rate_21_percent(self):
        assert apply_dynamic_tax(100, "LV") == 121.0
        assert apply_dynamic_tax(100, "lv") == 121.0
        assert apply_dynamic_tax(50, "LV") == 60.5

    def test_other_countries_20_percent(self):
        for country in ["US", "DE", "FR", "UK", "JP"]:
            assert apply_dynamic_tax(100, country) == 120.0
            assert apply_dynamic_tax(100, country.lower()) == 120.0

    def test_rounding(self):
        assert apply_dynamic_tax(0.83, "LV") == 1.0
        assert apply_dynamic_tax(0.83, "US") == 1.0

    def test_zero_net(self):
        assert apply_dynamic_tax(0, "LV") == 0
        assert apply_dynamic_tax(0, "US") == 0

    def test_empty_country(self):
        assert apply_dynamic_tax(100, "") == 120.0


class TestLoyaltyPointsEarned:
    def test_basic_calculation(self):
        assert loyalty_points_earned(100) == 2
        assert loyalty_points_earned(200) == 4
        assert loyalty_points_earned(50) == 1

    def test_floor_behavior(self):
        assert loyalty_points_earned(99) == 1
        assert loyalty_points_earned(149) == 2

    def test_zero_net(self):
        assert loyalty_points_earned(0) == 0

    def test_negative_net(self):
        assert loyalty_points_earned(-100) == -2

    def test_small_amounts(self):
        assert loyalty_points_earned(0.01) == 0
        assert loyalty_points_earned(49) == 0


class TestApplyLoyaltyDiscount:
    def test_no_points(self):
        assert apply_loyalty_discount(100, 0) == 100
        assert apply_loyalty_discount(100.50, 0) == 100.50

    def test_with_points_1_each(self):
        assert apply_loyalty_discount(100, 1) == 99.99
        assert apply_loyalty_discount(100, 50) == 99.50
        assert apply_loyalty_discount(100, 100) == 99.00

    def test_discount_exceeds_gross(self):
        assert apply_loyalty_discount(10, 2000) == 0.0
        assert apply_loyalty_discount(0.50, 100) == 0.0

    def test_rounding(self):
        assert apply_loyalty_discount(99.99, 1) == 99.98
        assert apply_loyalty_discount(99.99, 2) == 99.97
        assert apply_loyalty_discount(0.01, 1) == 0.0

    def test_zero_gross(self):
        assert apply_loyalty_discount(0, 100) == 0.0


class TestCapPrice:
    def test_price_below_cap(self):
        assert cap_price(50, 100) == 50
        assert cap_price(99.99, 100) == 99.99

    def test_price_above_cap(self):
        assert cap_price(150, 100) == 100
        assert cap_price(100.01, 100) == 100

    def test_price_equal_to_cap(self):
        assert cap_price(100, 100) == 100

    def test_zero_values(self):
        assert cap_price(0, 100) == 0
        assert cap_price(50, 0) == 0
        assert cap_price(0, 0) == 0

    def test_negative_values(self):
        assert cap_price(-50, 100) == -50
        assert cap_price(-50, -100) == -100


class TestRoundMoney:
    def test_default_two_decimals(self):
        assert round_money(1.2345) == 1.23
        assert round_money(1.235) == 1.24
        assert round_money(1.2344) == 1.23

    def test_custom_decimals(self):
        assert round_money(1.2345, 0) == 1.0
        assert round_money(1.2345, 1) == 1.2
        assert round_money(1.2345, 3) == 1.235
        assert round_money(1.2345, 4) == 1.2345

    def test_round_half_up(self):
        assert round_money(1.125, 2) == 1.13
        assert round_money(1.125, 1) == 1.1
        assert round_money(1.15, 1) == 1.2

    def test_negative_numbers(self):
        assert round_money(-1.2345) == -1.23
        assert round_money(-1.235) == -1.24
        assert round_money(-1.235, 1) == -1.2

    def test_integer_input(self):
        assert round_money(100) == 100.0


class TestIsWeekendRate:
    def test_monday_to_friday_are_weekdays(self):
        # 2024-01-01 is Monday
        for day in range(1, 6):
            d = datetime(2024, 1, day)
            assert is_weekend_rate(d) is False

    def test_saturday_and_sunday_are_weekends(self):
        assert is_weekend_rate(datetime(2024, 1, 6)) is True
        assert is_weekend_rate(datetime(2024, 1, 7)) is True

    def test_different_months(self):
        assert is_weekend_rate(datetime(2024, 2, 3)) is True
        assert is_weekend_rate(datetime(2024, 2, 5)) is False

    def test_boundary_midnight(self):
        assert is_weekend_rate(datetime(2024, 1, 6, 0, 0, 0)) is True
        assert is_weekend_rate(datetime(2024, 1, 6, 23, 59, 59)) is True


class TestEdgeCasesAndIntegration:
    def test_rounding_consistency(self):
        assert _round(1.005) == 1.01
        assert _round(1.004999) == 1.0

    def test_tax_rate_not_hardcoded(self):
        original_rate = TAX_RATE
        try:
            import billing.calculator as calc
            calc.TAX_RATE = 0.10
            assert calc.price_with_tax(100) != 121.0
        finally:
            calc.TAX_RATE = original_rate

    def test_booking_fee_not_hardcoded(self):
        import billing.calculator as calc
        original_fee = calc.BOOKING_FEE_PER_TICKET
        try:
            calc.BOOKING_FEE_PER_TICKET = 1.0
            assert calc.booking_fee(2) != 1.0
        finally:
            calc.BOOKING_FEE_PER_TICKET = original_fee

    def test_coupon_dictionary(self):
        assert apply_coupon(100, "some_coupon") == 100
        assert apply_coupon(100, "") == 100

    def test_split_payment_rounding(self):
        for _ in range(100):
            total = 100.00
            parts = 7
            result = split_payment(total, parts)
            assert abs(sum(result) - total) < 0.01
            assert len(result) == parts

    def test_loyalty_discount_never_negative(self):
        for gross in [0, 0.01, 1, 10, 100]:
            for points in [0, 1, 10, 100, 10000]:
                result = apply_loyalty_discount(gross, points)
                assert result >= 0
                assert result <= gross