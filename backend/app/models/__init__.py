"""Financial domain models.

Importing this package registers every table on ``app.db.Base.metadata``,
which the Alembic environment (for autogenerate) and tests rely on.
"""

from app.models.assets import Account, AccountAllocation, Liability
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
from app.models.flows import Expense, IncomeStream
from app.models.people import Household, Person, Plan

__all__ = [
    "Account",
    "AccountAllocation",
    "AccountType",
    "AssetClass",
    "Expense",
    "ExpenseCategory",
    "ExpenseClass",
    "FilingStatus",
    "Household",
    "IncomeStream",
    "IncomeType",
    "Liability",
    "LiabilityType",
    "MoneyBasis",
    "PaymentFrequency",
    "Person",
    "PersonRole",
    "Plan",
    "SpendingPhase",
    "SurvivorTreatment",
    "TaxClassification",
    "TaxTreatment",
]
