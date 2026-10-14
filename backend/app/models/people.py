"""Household, plan (baseline/scenario), and person models.

Ownership model (DECISIONS D-011): a ``Plan`` owns *all* of its financial
entities and people.  Scenarios are therefore structurally isolated from
the baseline — editing one plan can never mutate another, and deleting a
plan cascades to exactly its own rows.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import FilingStatus, PersonRole, db_enum


class Household(Base):
    """A planning group: the people and plans belong to this identity."""

    __tablename__ = "household"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filing_status: Mapped[FilingStatus] = mapped_column(
        db_enum(FilingStatus, "filing_status"), nullable=False
    )
    state_of_residence: Mapped[str | None] = mapped_column(String(2))
    planned_relocation_state: Mapped[str | None] = mapped_column(String(2))
    planned_relocation_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plans: Mapped[list[Plan]] = relationship(
        back_populates="household",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Plan(Base):
    """A baseline plan or an independent what-if scenario."""

    __tablename__ = "plan"
    __table_args__ = (
        # Exactly one baseline per household (scenario independence):
        Index(
            "uq_plan_single_baseline_per_household",
            "household_id",
            unique=True,
            postgresql_where=text("is_baseline"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(
        ForeignKey("household.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_baseline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Scenario lineage: the plan this scenario was duplicated from.
    parent_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plan.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    # Soft-hide for retired scenarios: archived plans stay readable and
    # individually retrievable but drop out of default listings.  The
    # baseline can never be archived (API guard, DECISIONS D-018).
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    household: Mapped[Household] = relationship(back_populates="plans")

    # Children are typed on the child side (they live in other modules);
    # DB-level ON DELETE CASCADE is the enforcement mechanism either way.
    people = relationship(
        "Person", back_populates="plan", cascade="all, delete-orphan", passive_deletes=True
    )
    accounts = relationship(
        "Account", back_populates="plan", cascade="all, delete-orphan", passive_deletes=True
    )
    liabilities = relationship(
        "Liability", back_populates="plan", cascade="all, delete-orphan", passive_deletes=True
    )
    income_streams = relationship(
        "IncomeStream", back_populates="plan", cascade="all, delete-orphan", passive_deletes=True
    )
    expenses = relationship(
        "Expense", back_populates="plan", cascade="all, delete-orphan", passive_deletes=True
    )


class Person(Base):
    """A primary person, spouse/partner, or dependent in a plan."""

    __tablename__ = "person"
    __table_args__ = (
        CheckConstraint(
            "longevity_age >= 40 AND longevity_age <= 120",
            name="ck_person_longevity_age",
        ),
        CheckConstraint(
            "dependent_until IS NULL OR dependent_from IS NULL "
            "OR dependent_until >= dependent_from",
            name="ck_person_dependency_period",
        ),
        CheckConstraint(
            "retirement_date IS NULL OR retirement_date >= date_of_birth",
            name="ck_person_retirement_after_birth",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plan.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[PersonRole] = mapped_column(
        db_enum(PersonRole, "person_role"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    longevity_age: Mapped[int] = mapped_column(nullable=False, default=95)
    retirement_date: Mapped[date | None] = mapped_column(Date)
    dependent_from: Mapped[date | None] = mapped_column(Date)
    dependent_until: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[Plan] = relationship(back_populates="people")
    owned_accounts = relationship(
        "Account",
        back_populates="owner_person",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
