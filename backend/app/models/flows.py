"""Income stream and expense models (recurring and one-time cash flows)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import (
    ExpenseCategory,
    ExpenseClass,
    IncomeType,
    MoneyBasis,
    PaymentFrequency,
    SpendingPhase,
    SurvivorTreatment,
    TaxClassification,
    db_enum,
)
from app.models.people import Person, Plan

MONEY = Numeric(20, 2)
RATE = Numeric(9, 6)


class IncomeStream(Base):
    """A recurring or one-time income source owned by a person in a plan."""

    __tablename__ = "income_stream"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_income_amount_non_negative"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_income_end_after_start",
        ),
        CheckConstraint(
            "growth_rate IS NULL OR (growth_rate > -1 AND growth_rate <= 1)",
            name="ck_income_growth_rate",
        ),
        CheckConstraint(
            "survivor_treatment IS NULL "
            "OR survivor_treatment <> 'reduce_by_percent' "
            "OR (survivor_percent IS NOT NULL AND survivor_percent > 0 AND survivor_percent <= 1)",
            name="ck_income_survivor_percent",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plan.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    income_type: Mapped[IncomeType] = mapped_column(
        db_enum(IncomeType, "income_type"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    frequency: Mapped[PaymentFrequency] = mapped_column(
        db_enum(PaymentFrequency, "payment_frequency"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    # Annual nominal growth as a fraction (0.03 = 3%/yr).
    growth_rate: Mapped[Decimal | None] = mapped_column(RATE)
    # nominal: grows with inflation rules; today_dollars: fixed purchasing power.
    basis: Mapped[MoneyBasis] = mapped_column(
        db_enum(MoneyBasis, "money_basis"), nullable=False, default=MoneyBasis.NOMINAL
    )
    tax_classification: Mapped[TaxClassification] = mapped_column(
        db_enum(TaxClassification, "tax_classification"), nullable=False
    )
    survivor_treatment: Mapped[SurvivorTreatment | None] = mapped_column(
        db_enum(SurvivorTreatment, "survivor_treatment")
    )
    survivor_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[Plan] = relationship(back_populates="income_streams")
    # One-way: the reverse direction lives on Account.owner_person only.
    owner_person: Mapped[Person] = relationship()


class Expense(Base):
    """A budget line: recurring or one-time spending with inflation rules."""

    __tablename__ = "expense"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_expense_amount_non_negative"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_expense_end_after_start",
        ),
        CheckConstraint(
            "inflation_rate IS NULL OR (inflation_rate > -1 AND inflation_rate <= 1)",
            name="ck_expense_inflation_rate",
        ),
        CheckConstraint(
            "(adjustment_age IS NULL) = (adjustment_percent IS NULL)",
            name="ck_expense_adjustment_pair",
        ),
        CheckConstraint(
            "adjustment_percent IS NULL OR (adjustment_percent >= -1 AND adjustment_percent <= 1)",
            name="ck_expense_adjustment_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plan.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    spending_class: Mapped[ExpenseClass] = mapped_column(
        db_enum(ExpenseClass, "expense_class"), nullable=False
    )
    category: Mapped[ExpenseCategory] = mapped_column(
        db_enum(ExpenseCategory, "expense_category"), nullable=False
    )
    # Free-text detail (e.g. which bill "other" refers to).
    category_detail: Mapped[str | None] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    frequency: Mapped[PaymentFrequency] = mapped_column(
        db_enum(PaymentFrequency, "payment_frequency"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    basis: Mapped[MoneyBasis] = mapped_column(
        db_enum(MoneyBasis, "money_basis"), nullable=False, default=MoneyBasis.NOMINAL
    )
    # Category-specific inflation override (fraction; None = plan-wide rate).
    inflation_rate: Mapped[Decimal | None] = mapped_column(RATE)
    phase: Mapped[SpendingPhase] = mapped_column(
        db_enum(SpendingPhase, "spending_phase"),
        nullable=False,
        default=SpendingPhase.ANY_TIME,
    )
    # One-time spending step at a given age (e.g. -0.25 at 70 = cut 25%).
    adjustment_age: Mapped[int | None] = mapped_column()
    adjustment_percent: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[Plan] = relationship(back_populates="expenses")
