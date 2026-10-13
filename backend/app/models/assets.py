"""Account, asset-allocation, and liability models."""

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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import AccountType, AssetClass, LiabilityType, TaxTreatment, db_enum
from app.models.people import Person, Plan

MONEY = Numeric(20, 2)
RATE = Numeric(9, 6)


class Account(Base):
    """A financial account or material asset with explicit tax treatment."""

    __tablename__ = "account"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_account_balance_non_negative"),
        CheckConstraint(
            "expected_return_rate IS NULL "
            "OR (expected_return_rate > -1 AND expected_return_rate <= 1)",
            name="ck_account_expected_return_rate",
        ),
        CheckConstraint(
            "fee_rate IS NULL OR (fee_rate >= 0 AND fee_rate <= 0.5)",
            name="ck_account_fee_rate",
        ),
        CheckConstraint(
            "annual_contribution IS NULL OR annual_contribution >= 0",
            name="ck_account_annual_contribution",
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
    account_type: Mapped[AccountType] = mapped_column(
        db_enum(AccountType, "account_type"), nullable=False
    )
    tax_treatment: Mapped[TaxTreatment] = mapped_column(
        db_enum(TaxTreatment, "tax_treatment"), nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    # Annual expected nominal return as a fraction (0.06 = 6%); None = plan default.
    expected_return_rate: Mapped[Decimal | None] = mapped_column(RATE)
    # Annual product fee as a fraction (0.0003 = 3 bps); None = plan default.
    fee_rate: Mapped[Decimal | None] = mapped_column(RATE)
    # Recurring annual contribution (salary deferrals are modeled as income).
    annual_contribution: Mapped[Decimal | None] = mapped_column(MONEY)
    acquired_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[Plan] = relationship(back_populates="accounts")
    owner_person: Mapped[Person] = relationship(back_populates="owned_accounts")
    allocations: Mapped[list[AccountAllocation]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AccountAllocation(Base):
    """Target asset-class weight for an account (weights sum to 1 across rows)."""

    __tablename__ = "account_allocation"
    __table_args__ = (
        UniqueConstraint("account_id", "asset_class", name="uq_account_allocation_class"),
        CheckConstraint("weight >= 0 AND weight <= 1", name="ck_allocation_weight_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_class: Mapped[AssetClass] = mapped_column(
        db_enum(AssetClass, "asset_class"), nullable=False
    )
    # Fraction of the account in this class (0.60 = 60%).
    weight: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped[Account] = relationship(back_populates="allocations")


class Liability(Base):
    """A debt: mortgage, HELOC, auto, student, credit card, or other."""

    __tablename__ = "liability"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_liability_balance_non_negative"),
        CheckConstraint(
            "interest_rate >= 0 AND interest_rate <= 1",
            name="ck_liability_interest_rate",
        ),
        CheckConstraint(
            "monthly_payment IS NULL OR monthly_payment >= 0",
            name="ck_liability_monthly_payment",
        ),
        CheckConstraint(
            "payoff_date IS NULL OR start_date IS NULL OR payoff_date >= start_date",
            name="ck_liability_payoff_after_start",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plan.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    liability_type: Mapped[LiabilityType] = mapped_column(
        db_enum(LiabilityType, "liability_type"), nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    monthly_payment: Mapped[Decimal | None] = mapped_column(MONEY)
    start_date: Mapped[date | None] = mapped_column(Date)
    payoff_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[Plan] = relationship(back_populates="liabilities")
