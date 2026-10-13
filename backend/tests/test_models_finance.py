"""Database-level tests for the financial domain model (DATA-001).

These exercise the schema *in PostgreSQL*: foreign-key cascades, CHECK
constraints, the partial unique baseline index, and enum validation —
independent of the Pydantic layer.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DataError, IntegrityError

from app.models.assets import Account, AccountAllocation, Liability
from app.models.enums import (
    AccountType,
    AssetClass,
    ExpenseCategory,
    ExpenseClass,
    FilingStatus,
    IncomeType,
    LiabilityType,
    PaymentFrequency,
    PersonRole,
    TaxClassification,
    TaxTreatment,
)
from app.models.flows import Expense, IncomeStream
from app.models.people import Household, Person, Plan


@pytest.fixture()
def plan_graph(db_session):
    """Household → baseline plan → primary person, flushed (ids assigned)."""
    household = Household(
        name="Graph Household",
        filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        state_of_residence="NJ",
    )
    plan = Plan(name="Baseline", is_baseline=True, household=household)
    person = Person(
        plan=plan,
        role=PersonRole.PRIMARY,
        name="Alex",
        date_of_birth=date(1980, 5, 1),
        longevity_age=90,
        retirement_date=date(2045, 5, 1),
    )
    db_session.add_all([household, plan, person])
    db_session.flush()
    return household, plan, person


def _add_full_cashflow_set(db_session, plan, person) -> None:
    account = Account(
        plan=plan,
        owner_person=person,
        name="401k",
        account_type=AccountType.TRADITIONAL_401K,
        tax_treatment=TaxTreatment.TAX_DEFERRED,
        balance=Decimal("75000.00"),
        expected_return_rate=Decimal("0.060000"),
        fee_rate=Decimal("0.000500"),
    )
    allocation = AccountAllocation(
        account=account, asset_class=AssetClass.US_STOCK, weight=Decimal("0.800000")
    )
    liability = Liability(
        plan=plan,
        name="Mortgage",
        liability_type=LiabilityType.MORTGAGE,
        balance=Decimal("200000.00"),
        interest_rate=Decimal("0.055000"),
        start_date=date(2018, 6, 1),
        payoff_date=date(2038, 6, 1),
    )
    income = IncomeStream(
        plan=plan,
        owner_person=person,
        name="Salary",
        income_type=IncomeType.SALARY,
        amount=Decimal("8500.00"),
        frequency=PaymentFrequency.MONTHLY,
        start_date=date(2026, 1, 1),
        tax_classification=TaxClassification.ORDINARY,
    )
    expense = Expense(
        plan=plan,
        name="Groceries",
        spending_class=ExpenseClass.DISCRETIONARY,
        category=ExpenseCategory.FOOD,
        amount=Decimal("650.00"),
        frequency=PaymentFrequency.MONTHLY,
        start_date=date(2026, 1, 1),
    )
    db_session.add_all([account, allocation, liability, income, expense])


def test_full_plan_graph_persists_and_resolves(db_session, plan_graph) -> None:
    _household, plan, person = plan_graph
    _add_full_cashflow_set(db_session, plan, person)
    db_session.commit()

    plan_id = plan.id
    db_session.expire_all()

    reloaded = db_session.get(Plan, plan_id)
    assert reloaded is not None
    assert [a.name for a in reloaded.accounts] == ["401k"]
    assert reloaded.accounts[0].owner_person.name == "Alex"
    assert reloaded.accounts[0].allocations[0].weight == Decimal("0.800000")
    assert [i.name for i in reloaded.income_streams] == ["Salary"]
    assert [e.name for e in reloaded.expenses] == ["Groceries"]
    assert [liab.name for liab in reloaded.liabilities] == ["Mortgage"]
    assert len(person.owned_accounts) == 1


def test_delete_plan_cascades_to_all_owned_rows(db_session, plan_graph) -> None:
    _household, plan, person = plan_graph
    _add_full_cashflow_set(db_session, plan, person)
    db_session.commit()
    household_id = plan.household_id

    db_session.delete(plan)
    db_session.commit()
    db_session.expire_all()

    assert db_session.scalar(select(func.count()).select_from(Plan)) == 0
    for model in (Person, Account, AccountAllocation, Liability, IncomeStream, Expense):
        assert db_session.scalar(select(func.count()).select_from(model)) == 0, model.__name__
    # household and its baseline protection survive
    assert db_session.get(Household, household_id) is not None


def test_delete_household_cascades_to_plans(db_session, plan_graph) -> None:
    household, _plan, _person = plan_graph
    db_session.commit()
    household_id = household.id

    db_session.delete(household)
    db_session.commit()

    assert db_session.get(Household, household_id) is None
    assert db_session.scalar(select(func.count()).select_from(Plan)) == 0


def test_deleting_person_cascades_to_their_accounts(db_session, plan_graph) -> None:
    _household, plan, person = plan_graph
    account = Account(
        plan=plan,
        owner_person=person,
        name="Checking",
        account_type=AccountType.CHECKING,
        tax_treatment=TaxTreatment.TAXABLE,
        balance=Decimal("2500.00"),
    )
    db_session.add(account)
    db_session.commit()

    db_session.delete(person)
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(Account)) == 0


def test_negative_account_balance_rejected_by_database(db_session, plan_graph) -> None:
    _household, plan, person = plan_graph
    db_session.add(
        Account(
            plan=plan,
            owner_person=person,
            name="Overdrawn",
            account_type=AccountType.CHECKING,
            tax_treatment=TaxTreatment.TAXABLE,
            balance=Decimal("-0.01"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_second_baseline_in_same_household_rejected(db_session, plan_graph) -> None:
    _household, plan, _person = plan_graph
    db_session.add(
        Plan(name="Pretender", is_baseline=True, household_id=plan.household_id)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_baseline_allowed_in_a_different_household(db_session, plan_graph) -> None:
    _household, _plan, _person = plan_graph
    other = Household(name="Other", filing_status=FilingStatus.SINGLE)
    db_session.add(Plan(name="Their baseline", is_baseline=True, household=other))
    db_session.commit()  # partial unique index is per-household

    assert (
        db_session.scalar(
            select(func.count()).select_from(Plan).where(Plan.is_baseline.is_(True))
        )
        == 2
    )


def test_duplicate_asset_class_in_allocation_rejected(db_session, plan_graph) -> None:
    _household, plan, person = plan_graph
    account = Account(
        plan=plan,
        owner_person=person,
        name="IRA",
        account_type=AccountType.TRADITIONAL_IRA,
        tax_treatment=TaxTreatment.TAX_DEFERRED,
        balance=Decimal("1000.00"),
    )
    db_session.add_all(
        [
            account,
            AccountAllocation(
                account=account, asset_class=AssetClass.BONDS, weight=Decimal("0.5")
            ),
            AccountAllocation(
                account=account, asset_class=AssetClass.BONDS, weight=Decimal("0.5")
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_end_date_before_start_date_rejected_by_database(db_session, plan_graph) -> None:
    _household, plan, person = plan_graph
    db_session.add(
        IncomeStream(
            plan=plan,
            owner_person=person,
            name="Backwards",
            income_type=IncomeType.PENSION,
            amount=Decimal("100.00"),
            frequency=PaymentFrequency.ANNUAL,
            start_date=date(2030, 1, 1),
            end_date=date(2029, 1, 1),
            tax_classification=TaxClassification.ORDINARY,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_partial_expense_adjustment_rejected_by_database(db_session, plan_graph) -> None:
    _household, plan, _person = plan_graph
    db_session.add(
        Expense(
            plan=plan,
            name="Half-adjusted",
            spending_class=ExpenseClass.ESSENTIAL,
            category=ExpenseCategory.HOUSING,
            amount=Decimal("2000.00"),
            frequency=PaymentFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            adjustment_age=70,
            # adjustment_percent intentionally missing
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unknown_enum_value_rejected_by_database(db_session, plan_graph) -> None:
    """The PG enum type is the backstop when data bypasses the API."""
    with pytest.raises(DataError):
        db_session.execute(
            text(
                "INSERT INTO household (name, filing_status) "
                "VALUES ('Bogus', 'not_a_real_filing_status')"
            )
        )
    db_session.rollback()
