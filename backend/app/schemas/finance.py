"""Pydantic input schemas for the financial domain (DATA-001).

These schemas are the authoritative input-validation layer: friendly,
field-level rejection of invalid dates, amounts, rates, enums, and
cross-field inconsistencies. The database CHECK constraints and foreign
keys remain the backstop if data bypasses the API.

Conventions
-----------
* Amounts are non-negative ``Decimal`` values (no currency symbols).
* Rates are annual fractions: ``0.03`` means 3%/yr.
* Dates are ISO calendar dates; ``end_date`` must not precede ``start_date``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    AccountType,
    AssetClass,
    ExpenseCategory,
    ExpenseClass,
    FilingStatus,
    IncomeType,
    LiabilityType,
    MoneyBasis,
    PaymentFrequency,
    PersonRole,
    SpendingPhase,
    SurvivorTreatment,
    TaxClassification,
    TaxTreatment,
)

US_STATE_PATTERN = "^[A-Z]{2}$"

# Annotated field types shared across schemas.
Money = Annotated[Decimal, Field(ge=0)]
Rate = Annotated[Decimal, Field(gt=-1, le=1)]  # annual fraction, e.g. 0.06
FeeRate = Annotated[Decimal, Field(ge=0, le=0.5)]
Weight = Annotated[Decimal, Field(ge=0, le=1)]
SurvivorFraction = Annotated[Decimal, Field(gt=0, le=1)]
Percent = Annotated[Decimal, Field(ge=-1, le=1)]  # signed, e.g. -0.25 = -25%
PersonRef = Annotated[int, Field(gt=0)]


class _StrictModel(BaseModel):
    """Base: forbid unknown fields and strip surrounding whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _require_date_order(
    start: date | None, end: date | None, start_name: str, end_name: str
) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError(f"{end_name} ({end}) must not precede {start_name} ({start})")


def _require_one_time_end(frequency: PaymentFrequency, start: date, end: date | None) -> None:
    if frequency is PaymentFrequency.ONE_TIME and end is not None and end != start:
        raise ValueError("end_date must equal start_date (or be null) for one_time flows")


class HouseholdCreate(_StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    filing_status: FilingStatus
    state_of_residence: Annotated[str | None, Field(pattern=US_STATE_PATTERN)] = None
    planned_relocation_state: Annotated[str | None, Field(pattern=US_STATE_PATTERN)] = None
    planned_relocation_date: date | None = None

    @field_validator("state_of_residence", "planned_relocation_state", mode="before")
    @classmethod
    def _normalize_state_code(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _relocation_date_requires_state(self) -> HouseholdCreate:
        if self.planned_relocation_date and not self.planned_relocation_state:
            raise ValueError(
                "planned_relocation_state is required when planned_relocation_date is set"
            )
        return self


class PlanCreate(_StrictModel):
    """A new plan; scenarios set ``parent_plan_id`` to their source plan.

    ``is_baseline`` may be combined with ``parent_plan_id`` only when a
    scenario is promoted to baseline (lineage is preserved on purpose).
    Exactly one baseline per household is enforced by a partial unique index.
    """

    name: Annotated[str, Field(min_length=1, max_length=255)]
    is_baseline: bool = False
    parent_plan_id: PersonRef | None = None
    notes: Annotated[str | None, Field(max_length=10_000)] = None


class PersonCreate(_StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    role: PersonRole
    date_of_birth: date
    longevity_age: Annotated[int, Field(ge=40, le=120)] = 95
    retirement_date: date | None = None
    dependent_from: date | None = None
    dependent_until: date | None = None

    @field_validator("date_of_birth")
    @classmethod
    def _date_of_birth_must_be_in_the_past(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return value

    @model_validator(mode="after")
    def _cross_date_rules(self) -> PersonCreate:
        if self.retirement_date is not None and self.retirement_date < self.date_of_birth:
            raise ValueError("retirement_date must not precede date_of_birth")
        _require_date_order(
            self.dependent_from, self.dependent_until, "dependent_from", "dependent_until"
        )
        has_dependency_window = self.dependent_from is not None or self.dependent_until is not None
        if has_dependency_window and self.role is not PersonRole.DEPENDENT:
            raise ValueError("dependency dates are only valid when role='dependent'")
        return self


class AccountCreate(_StrictModel):
    owner_person_id: PersonRef
    name: Annotated[str, Field(min_length=1, max_length=255)]
    account_type: AccountType
    tax_treatment: TaxTreatment
    balance: Money
    expected_return_rate: Rate | None = None
    fee_rate: FeeRate | None = None
    annual_contribution: Money | None = None
    acquired_date: date | None = None


class AllocationCreate(_StrictModel):
    """One asset-class weight (a set of these must sum to exactly 1)."""

    asset_class: AssetClass
    weight: Weight


class AccountDraft(_StrictModel):
    """An account plus its optional allocation, validated as a set."""

    account: AccountCreate
    allocations: list[AllocationCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _allocation_set_must_be_complete(self) -> AccountDraft:
        if not self.allocations:
            return self
        classes = [item.asset_class for item in self.allocations]
        if len(classes) != len(set(classes)):
            raise ValueError("allocations contain a duplicate asset class")
        total = sum((item.weight for item in self.allocations), start=Decimal("0"))
        if total != Decimal("1"):
            raise ValueError(f"allocation weights must sum to exactly 1, got {total}")
        return self


class LiabilityCreate(_StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    liability_type: LiabilityType
    balance: Money
    interest_rate: Annotated[Decimal, Field(ge=0, le=1)]
    monthly_payment: Money | None = None
    start_date: date | None = None
    payoff_date: date | None = None
    notes: Annotated[str | None, Field(max_length=10_000)] = None

    @model_validator(mode="after")
    def _date_order(self) -> LiabilityCreate:
        _require_date_order(self.start_date, self.payoff_date, "start_date", "payoff_date")
        return self


class IncomeStreamCreate(_StrictModel):
    owner_person_id: PersonRef
    name: Annotated[str, Field(min_length=1, max_length=255)]
    income_type: IncomeType
    amount: Money
    frequency: PaymentFrequency
    start_date: date
    end_date: date | None = None
    growth_rate: Rate | None = None
    basis: MoneyBasis = MoneyBasis.NOMINAL
    tax_classification: TaxClassification
    survivor_treatment: SurvivorTreatment | None = None
    survivor_percent: SurvivorFraction | None = None

    @model_validator(mode="after")
    def _cross_rules(self) -> IncomeStreamCreate:
        _require_date_order(self.start_date, self.end_date, "start_date", "end_date")
        _require_one_time_end(self.frequency, self.start_date, self.end_date)
        if self.survivor_treatment is None and self.survivor_percent is not None:
            raise ValueError("survivor_percent requires survivor_treatment")
        if self.survivor_treatment is SurvivorTreatment.REDUCE_BY_PERCENT:
            if self.survivor_percent is None:
                raise ValueError("survivor_treatment='reduce_by_percent' requires survivor_percent")
        elif self.survivor_percent is not None:
            raise ValueError(
                "survivor_percent is only valid with survivor_treatment='reduce_by_percent'"
            )
        return self


class ExpenseCreate(_StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    spending_class: ExpenseClass
    category: ExpenseCategory
    category_detail: Annotated[str | None, Field(max_length=120)] = None
    amount: Money
    # Budgets are predominantly monthly, hence the default.
    frequency: PaymentFrequency = PaymentFrequency.MONTHLY
    start_date: date
    end_date: date | None = None
    basis: MoneyBasis = MoneyBasis.NOMINAL
    inflation_rate: Rate | None = None
    phase: SpendingPhase = SpendingPhase.ANY_TIME
    adjustment_age: Annotated[int | None, Field(ge=18, le=120)] = None
    adjustment_percent: Percent | None = None

    @model_validator(mode="after")
    def _cross_rules(self) -> ExpenseCreate:
        _require_date_order(self.start_date, self.end_date, "start_date", "end_date")
        _require_one_time_end(self.frequency, self.start_date, self.end_date)
        if self.category is ExpenseCategory.OTHER and not self.category_detail:
            raise ValueError("category_detail is required when category='other'")
        if (self.adjustment_age is None) != (self.adjustment_percent is None):
            raise ValueError("adjustment_age and adjustment_percent must be set together")
        return self
