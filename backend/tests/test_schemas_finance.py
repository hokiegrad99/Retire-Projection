"""Validation tests for the financial domain input schemas (DATA-001).

Pure validation — no database required.  Each rejected-input test documents
a rule the API must never let through.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.finance import (
    AccountCreate,
    AccountDraft,
    AllocationCreate,
    ExpenseCreate,
    HouseholdCreate,
    IncomeStreamCreate,
    LiabilityCreate,
    PersonCreate,
)

TODAY = date.today()


def _household(**overrides) -> HouseholdCreate:
    data: dict = {"name": "Demo Household", "filing_status": "single"}
    data.update(overrides)
    return HouseholdCreate(**data)


def _person(**overrides) -> PersonCreate:
    data: dict = {"name": "Alex", "role": "primary", "date_of_birth": date(1980, 5, 1)}
    data.update(overrides)
    return PersonCreate(**data)


def _account(**overrides) -> AccountCreate:
    data: dict = {
        "owner_person_id": 1,
        "name": "Brokerage",
        "account_type": "taxable_brokerage",
        "tax_treatment": "taxable",
        "balance": "10000.00",
    }
    data.update(overrides)
    return AccountCreate(**data)


def _income(**overrides) -> IncomeStreamCreate:
    data: dict = {
        "owner_person_id": 1,
        "name": "Salary",
        "income_type": "salary",
        "amount": "5000.00",
        "frequency": "monthly",
        "start_date": date(2026, 1, 1),
        "tax_classification": "ordinary",
    }
    data.update(overrides)
    return IncomeStreamCreate(**data)


def _expense(**overrides) -> ExpenseCreate:
    data: dict = {
        "name": "Groceries",
        "spending_class": "discretionary",
        "category": "food",
        "amount": "600.00",
        "start_date": date(2026, 1, 1),
    }
    data.update(overrides)
    return ExpenseCreate(**data)


# --- household -------------------------------------------------------------


def test_household_accepts_and_normalizes_state_code() -> None:
    household = _household(state_of_residence="nj")
    assert household.state_of_residence == "NJ"
    assert household.filing_status.value == "single"


def test_household_rejects_invalid_state_code() -> None:
    with pytest.raises(ValidationError):
        _household(state_of_residence="NOT_A_STATE")


def test_household_relocation_date_requires_state() -> None:
    with pytest.raises(ValidationError, match="relocation_state is required"):
        _household(planned_relocation_date=date(2031, 6, 1))


def test_household_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _household(ssn_secret="should-never-be-stored")


# --- person ----------------------------------------------------------------


def test_person_accepts_realistic_values() -> None:
    person = _person(longevity_age=92, retirement_date=date(2045, 6, 1))
    assert person.longevity_age == 92


def test_person_rejects_future_date_of_birth() -> None:
    with pytest.raises(ValidationError, match="past"):
        _person(date_of_birth=TODAY + timedelta(days=1))


def test_person_longevity_age_bounds() -> None:
    _person(longevity_age=40)
    _person(longevity_age=120)
    with pytest.raises(ValidationError):
        _person(longevity_age=39)
    with pytest.raises(ValidationError):
        _person(longevity_age=121)


def test_person_rejects_retirement_before_birth() -> None:
    with pytest.raises(ValidationError, match="retirement_date"):
        _person(retirement_date=date(1970, 1, 1))


def test_person_dependency_window_must_be_ordered() -> None:
    with pytest.raises(ValidationError, match="dependent_until"):
        _person(role="dependent", dependent_from=date(2030, 1, 1), dependent_until=date(2029, 1, 1))


def test_person_dependency_dates_require_dependent_role() -> None:
    with pytest.raises(ValidationError, match="only valid when role="):
        _person(dependent_from=date(2020, 1, 1))


# --- accounts and allocations ---------------------------------------------


def test_account_rejects_negative_balance() -> None:
    with pytest.raises(ValidationError):
        _account(balance="-0.01")


def test_account_rejects_out_of_range_rates() -> None:
    with pytest.raises(ValidationError):
        _account(expected_return_rate="1.5")
    with pytest.raises(ValidationError):
        _account(fee_rate="0.9")


def test_allocation_set_must_sum_to_one() -> None:
    draft = AccountDraft(
        account=_account(),
        allocations=[
            AllocationCreate(asset_class="us_stock", weight="0.6"),
            AllocationCreate(asset_class="bonds", weight="0.4"),
        ],
    )
    assert sum(item.weight for item in draft.allocations) == Decimal("1")


def test_allocation_set_rejects_partial_weights() -> None:
    with pytest.raises(ValidationError, match="sum to exactly 1"):
        AccountDraft(
            account=_account(),
            allocations=[
                AllocationCreate(asset_class="us_stock", weight="0.6"),
                AllocationCreate(asset_class="bonds", weight="0.3"),
            ],
        )


def test_allocation_set_rejects_duplicate_asset_class() -> None:
    with pytest.raises(ValidationError, match="duplicate asset class"):
        AccountDraft(
            account=_account(),
            allocations=[
                AllocationCreate(asset_class="us_stock", weight="0.5"),
                AllocationCreate(asset_class="us_stock", weight="0.5"),
            ],
        )


def test_account_draft_allows_empty_allocation() -> None:
    draft = AccountDraft(account=_account())
    assert draft.allocations == []


# --- liabilities -----------------------------------------------------------


def test_liability_rejects_payoff_before_start() -> None:
    with pytest.raises(ValidationError, match="payoff_date"):
        LiabilityCreate(
            name="Mortgage",
            liability_type="mortgage",
            balance="250000.00",
            interest_rate="0.055",
            start_date=date(2020, 1, 1),
            payoff_date=date(2019, 12, 31),
        )


# --- income ----------------------------------------------------------------


def test_income_rejects_end_before_start() -> None:
    with pytest.raises(ValidationError, match="end_date"):
        _income(start_date=date(2030, 1, 1), end_date=date(2029, 1, 1))


def test_income_one_time_flow_cannot_span_dates() -> None:
    with pytest.raises(ValidationError, match="one_time"):
        _income(frequency="one_time", end_date=date(2027, 1, 1))


def test_income_survivor_rules() -> None:
    # percent without treatment
    with pytest.raises(ValidationError, match="survivor_treatment"):
        _income(survivor_percent="0.5")
    # treatment without required percent
    with pytest.raises(ValidationError, match="survivor_percent"):
        _income(survivor_treatment="reduce_by_percent")
    # valid pairing
    ok = _income(survivor_treatment="reduce_by_percent", survivor_percent="0.6")
    assert ok.survivor_percent == Decimal("0.6")


def test_income_rejects_negative_amount() -> None:
    with pytest.raises(ValidationError):
        _income(amount="-100")


# --- expenses --------------------------------------------------------------


def test_expense_defaults_are_documented_values() -> None:
    expense = _expense()
    assert expense.frequency.value == "monthly"
    assert expense.basis.value == "nominal"
    assert expense.phase.value == "any_time"


def test_expense_adjustment_requires_both_fields() -> None:
    with pytest.raises(ValidationError, match="set together"):
        _expense(adjustment_age=70)
    with pytest.raises(ValidationError, match="set together"):
        _expense(adjustment_percent=Decimal("-0.25"))
    # valid pairing (both set)
    _expense(adjustment_age=70, adjustment_percent=Decimal("-0.25"))


def test_expense_rejects_out_of_range_adjustment() -> None:
    with pytest.raises(ValidationError):
        _expense(adjustment_age=70, adjustment_percent=Decimal("1.5"))


def test_expense_other_category_requires_detail() -> None:
    with pytest.raises(ValidationError, match="category_detail"):
        _expense(category="other")
    ok = _expense(category="other", category_detail="Sonder subscription")
    assert ok.category_detail == "Sonder subscription"
