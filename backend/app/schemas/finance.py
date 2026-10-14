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

from datetime import date, datetime
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


def validate_allocation_set(allocations: list[AllocationCreate]) -> None:
    """A non-empty allocation set must use each class once and sum to exactly 1.

    Shared by the draft schema (create) and the account PATCH path so the
    rule has exactly one implementation (see DECISIONS D-011).
    """
    if not allocations:
        return
    classes = [item.asset_class for item in allocations]
    if len(classes) != len(set(classes)):
        raise ValueError("allocations contain a duplicate asset class")
    total = sum((item.weight for item in allocations), start=Decimal("0"))
    if total != Decimal("1"):
        raise ValueError(f"allocation weights must sum to exactly 1, got {total}")


class AccountDraft(_StrictModel):
    """An account plus its optional allocation, validated as a set."""

    account: AccountCreate
    allocations: list[AllocationCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _allocation_set_must_be_complete(self) -> AccountDraft:
        validate_allocation_set(self.allocations)
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


# ---------------------------------------------------------------------------
# DATA-002: API read models (ORM -> JSON) and partial-update (PATCH) models.
#
# PATCH semantics: fields omitted keep their current value; a field sent as
# explicit null clears it. Cross-field rules are re-validated on the *merged*
# record by reusing the *Create schemas (see services/crud.py), so PATCH
# cannot smuggle in states a POST would have rejected.
# ---------------------------------------------------------------------------


class _ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HouseholdRead(_ReadModel):
    id: int
    name: str
    filing_status: FilingStatus
    state_of_residence: str | None
    planned_relocation_state: str | None
    planned_relocation_date: date | None
    created_at: datetime
    updated_at: datetime


class PlanRead(_ReadModel):
    id: int
    household_id: int
    name: str
    is_baseline: bool
    parent_plan_id: int | None
    notes: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PersonRead(_ReadModel):
    id: int
    plan_id: int
    role: PersonRole
    name: str
    date_of_birth: date
    longevity_age: int
    retirement_date: date | None
    dependent_from: date | None
    dependent_until: date | None
    created_at: datetime
    updated_at: datetime


class AllocationRead(_ReadModel):
    id: int
    asset_class: AssetClass
    weight: Decimal


class AccountRead(_ReadModel):
    id: int
    plan_id: int
    owner_person_id: int
    name: str
    account_type: AccountType
    tax_treatment: TaxTreatment
    balance: Decimal
    expected_return_rate: Decimal | None
    fee_rate: Decimal | None
    annual_contribution: Decimal | None
    acquired_date: date | None
    allocations: list[AllocationRead] = []
    created_at: datetime
    updated_at: datetime


class LiabilityRead(_ReadModel):
    id: int
    plan_id: int
    name: str
    liability_type: LiabilityType
    balance: Decimal
    interest_rate: Decimal
    monthly_payment: Decimal | None
    start_date: date | None
    payoff_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class IncomeStreamRead(_ReadModel):
    id: int
    plan_id: int
    owner_person_id: int
    name: str
    income_type: IncomeType
    amount: Decimal
    frequency: PaymentFrequency
    start_date: date
    end_date: date | None
    growth_rate: Decimal | None
    basis: MoneyBasis
    tax_classification: TaxClassification
    survivor_treatment: SurvivorTreatment | None
    survivor_percent: Decimal | None
    created_at: datetime
    updated_at: datetime


class ExpenseRead(_ReadModel):
    id: int
    plan_id: int
    name: str
    spending_class: ExpenseClass
    category: ExpenseCategory
    category_detail: str | None
    amount: Decimal
    frequency: PaymentFrequency
    start_date: date
    end_date: date | None
    basis: MoneyBasis
    inflation_rate: Decimal | None
    phase: SpendingPhase
    adjustment_age: int | None
    adjustment_percent: Decimal | None
    created_at: datetime
    updated_at: datetime


class HouseholdPatch(_StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    filing_status: FilingStatus | None = None
    state_of_residence: Annotated[str, Field(pattern=US_STATE_PATTERN)] | None = None
    planned_relocation_state: Annotated[str, Field(pattern=US_STATE_PATTERN)] | None = None
    planned_relocation_date: date | None = None

    @field_validator("state_of_residence", "planned_relocation_state", mode="before")
    @classmethod
    def _normalize_state_code(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


class PlanPatch(_StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    notes: Annotated[str | None, Field(max_length=10_000)] = None
    # True = promote this plan to baseline (demotes the current one); the
    # merge-validation in PlanCreate guarantees a household never holds two.
    is_baseline: bool | None = None
    parent_plan_id: PersonRef | None = None
    # True = archive (soft-hide from default listings), False = restore.
    # Handled by the plan router: the baseline can never be archived and an
    # archived plan can never be promoted (DECISIONS D-018).
    archived: bool | None = None


class PlanDuplicate(_StrictModel):
    """Body for ``POST /api/plans/{id}/duplicate`` (DATA-003).

    Omitted ``name`` becomes "<source name> (copy)"; the duplicate always
    starts as a scenario (``parent_plan_id`` records the source) unless the
    household has no baseline yet and one is requested.
    """

    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    is_baseline: bool = False


# --- plan comparison (DATA-003, spec §13) -----------------------------------

# Scalar reported for a differing field: JSON-safe normalized value.
DiffValue = str | int | bool | None


class PlanSide(_ReadModel):
    """Identity of one side of a comparison."""

    id: int
    name: str
    is_baseline: bool
    archived_at: datetime | None


class PlanFieldDifference(_ReadModel):
    """One field where the two plans diverge, keyed by entity name."""

    entity: str  # plan | person | account | liability | income_stream | expense
    key: str  # the row's name within its entity ("plan" for the plan row)
    field: str
    left: DiffValue
    right: DiffValue


class PlanEntityPresence(_ReadModel):
    """An entity that exists on only one side of the comparison."""

    entity: str
    key: str


class PlanComparison(_ReadModel):
    """Field-level diff of two plans in the same household (spec §13)."""

    left: PlanSide
    right: PlanSide
    differences: list[PlanFieldDifference]
    only_in_left: list[PlanEntityPresence]
    only_in_right: list[PlanEntityPresence]


class PersonPatch(_StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    role: PersonRole | None = None
    date_of_birth: date | None = None
    longevity_age: Annotated[int, Field(ge=40, le=120)] | None = None
    retirement_date: date | None = None
    dependent_from: date | None = None
    dependent_until: date | None = None


class AccountPatch(_StrictModel):
    owner_person_id: PersonRef | None = None
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    account_type: AccountType | None = None
    tax_treatment: TaxTreatment | None = None
    balance: Money | None = None
    expected_return_rate: Rate | None = None
    fee_rate: FeeRate | None = None
    annual_contribution: Money | None = None
    acquired_date: date | None = None
    # Replace-the-whole-set semantics; null/omitted keeps the current set.
    allocations: list[AllocationCreate] | None = None


class LiabilityPatch(_StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    liability_type: LiabilityType | None = None
    balance: Money | None = None
    interest_rate: Annotated[Decimal, Field(ge=0, le=1)] | None = None
    monthly_payment: Money | None = None
    start_date: date | None = None
    payoff_date: date | None = None
    notes: Annotated[str | None, Field(max_length=10_000)] = None


class IncomeStreamPatch(_StrictModel):
    owner_person_id: PersonRef | None = None
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    income_type: IncomeType | None = None
    amount: Money | None = None
    frequency: PaymentFrequency | None = None
    start_date: date | None = None
    end_date: date | None = None
    growth_rate: Rate | None = None
    basis: MoneyBasis | None = None
    tax_classification: TaxClassification | None = None
    survivor_treatment: SurvivorTreatment | None = None
    survivor_percent: SurvivorFraction | None = None


class ExpensePatch(_StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    spending_class: ExpenseClass | None = None
    category: ExpenseCategory | None = None
    category_detail: Annotated[str | None, Field(max_length=120)] = None
    amount: Money | None = None
    frequency: PaymentFrequency | None = None
    start_date: date | None = None
    end_date: date | None = None
    basis: MoneyBasis | None = None
    inflation_rate: Rate | None = None
    phase: SpendingPhase | None = None
    adjustment_age: Annotated[int | None, Field(ge=18, le=120)] = None
    adjustment_percent: Percent | None = None
