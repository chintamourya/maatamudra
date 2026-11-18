from datetime import date

import pytest

from app.models import RentalSpec


@pytest.fixture
def spec() -> RentalSpec:
    return RentalSpec(
        state="Telangana", city="Hyderabad", landlord_name="Ravi Kumar", tenant_name="Anita Rao",
        property_address="Flat 302, Green Heights, Madhapur, Hyderabad", start_date=date(2026, 12, 1),
        term_months=11, monthly_rent=22000, security_deposit=44000, due_day=5, notice_days=30,
        grace_days=5, late_fee_per_day=50, default_threshold_days=30, cure_days=15,
        deposit_refund_days=30, lock_in_months=6,
    )
