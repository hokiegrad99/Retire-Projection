"""Scenario management (DATA-003): deep-copy duplication and plan diffing.

Kept out of ``crud.py``, which stays generic: duplication and comparison are
plan-specific orchestration (DECISIONS D-018 archive semantics, D-019 diff
matching).

Design notes:

* ``copy_plan`` clones every owned row by copying column values as *Python
  objects* — no serialization round-trip, so ``Decimal`` precision and date
  types survive exactly.  People are copied first so dependents can remap
  their ``owner_person_id`` to the new person ids.
* ``diff_plans`` matches rows by name within each entity (ties broken by id
  order) and reports scalar field differences plus presence differences.
  Owner references are reported as the owner's *name* (ids differ by
  construction across plans) and allocations as a canonical summary string.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.people import Plan
from app.schemas.finance import (
    PlanComparison,
    PlanDuplicate,
    PlanEntityPresence,
    PlanFieldDifference,
    PlanSide,
)

# Never copied or diffed: identity, audit stamps, and per-row ownership FKs
# (plan_id is implied by the copy; owner_person_id is remapped/reported by name).
_SKIP_COLUMNS = frozenset({"id", "plan_id", "created_at", "updated_at", "owner_person_id"})


def _clone[ModelT: object](
    source: ModelT, skip: frozenset[str], **overrides: object
) -> ModelT:
    """Copy every column of ``source`` except identity/audit/skipped ones."""
    clone = type(source)()
    for column in source.__table__.columns.keys():  # type: ignore[attr-defined]
        if column in _SKIP_COLUMNS or column in skip:
            continue
        setattr(clone, column, getattr(source, column))
    for name, value in overrides.items():
        setattr(clone, name, value)
    return clone


def copy_plan(db: Session, source: Plan, payload: PlanDuplicate) -> Plan:
    """Deep-copy ``source`` into a new plan of the same household.

    The copy starts as a scenario (``parent_plan_id`` = source, lineage
    kept on purpose) unless a baseline is explicitly requested and the
    household has none yet (409 otherwise, mirroring plan creation).
    """
    if payload.is_baseline:
        existing = db.scalar(
            select(Plan.id).where(
                Plan.household_id == source.household_id,
                Plan.is_baseline.is_(True),
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "household already has a baseline plan; promote a scenario "
                    "with PATCH /api/plans/{id} {\"is_baseline\": true} instead"
                ),
            )

    copy = _clone(
        source,
        skip=frozenset(),
        name=payload.name or f"{source.name} (copy)",
        is_baseline=payload.is_baseline,
        parent_plan_id=source.id,
        # Archived is a soft-hide state, not an assumption: a copy starts live.
        archived_at=None,
    )
    db.add(copy)
    db.flush()  # assigns copy.id before children reference it

    person_ids: dict[int, int] = {}
    for person in source.people:
        clone = _clone(person, skip=frozenset({"plan_id"}), plan_id=copy.id)
        db.add(clone)
        db.flush()
        person_ids[person.id] = clone.id

    for account in source.accounts:
        # Defensive: the API keeps owners in-plan, but direct DB writes could
        # violate that; fail loudly instead of silently dropping a row.
        owner_id = person_ids.get(account.owner_person_id)
        if owner_id is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"cannot duplicate: account {account.id} is owned by a person "
                    f"outside plan {source.id}"
                ),
            )
        clone = _clone(
            account,
            skip=frozenset({"owner_person_id"}),
            plan_id=copy.id,
            owner_person_id=owner_id,
        )
        db.add(clone)
        db.flush()
        for allocation in account.allocations:
            db.add(
                _clone(
                    allocation,
                    skip=frozenset({"account_id"}),
                    account_id=clone.id,
                )
            )

    for liability in source.liabilities:
        db.add(_clone(liability, skip=frozenset(), plan_id=copy.id))

    for stream in source.income_streams:
        owner_id = person_ids.get(stream.owner_person_id)
        if owner_id is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"cannot duplicate: income stream {stream.id} is owned by a "
                    f"person outside plan {source.id}"
                ),
            )
        db.add(
            _clone(
                stream,
                skip=frozenset({"owner_person_id"}),
                plan_id=copy.id,
                owner_person_id=owner_id,
            )
        )

    for expense in source.expenses:
        db.add(_clone(expense, skip=frozenset(), plan_id=copy.id))

    db.commit()
    db.refresh(copy)
    return copy


# --- comparison --------------------------------------------------------------


def _scalar(value: object) -> str | int | bool | None:
    """Normalize a column value to a JSON-safe scalar for reporting."""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)  # pragma: no cover - defensive for future column types


def _pair_by_name(left_rows: list, right_rows: list) -> tuple[list, list, list]:
    """Match rows by name; ties are paired in id order (D-019)."""
    unmatched_right: dict[str, list] = {}
    for row in sorted(right_rows, key=lambda item: item.id):
        unmatched_right.setdefault(row.name, []).append(row)
    matched: list[tuple] = []
    only_left: list = []
    for row in sorted(left_rows, key=lambda item: item.id):
        bucket = unmatched_right.get(row.name)
        if bucket:
            matched.append((row, bucket.pop(0)))
        else:
            only_left.append(row)
    only_right = sorted(
        (row for bucket in unmatched_right.values() for row in bucket),
        key=lambda item: item.id,
    )
    return matched, only_left, only_right


def _owner_name(row: object) -> str:
    return row.owner_person.name  # type: ignore[attr-defined,no-any-return]


def _allocation_summary(account: object) -> str:
    return ", ".join(
        f"{allocation.asset_class}={allocation.weight}"
        for allocation in sorted(
            account.allocations, key=lambda item: str(item.asset_class)  # type: ignore[attr-defined]
        )
    )  # type: ignore[no-any-return]


def _derived_values(entity: str, left_row: object, right_row: object) -> dict[str, tuple]:
    """Values not stored as plain columns on the row (owner names, allocations)."""
    if entity == "account":
        return {
            "owner": (_owner_name(left_row), _owner_name(right_row)),
            "allocations": (_allocation_summary(left_row), _allocation_summary(right_row)),
        }
    if entity == "income_stream":
        return {"owner": (_owner_name(left_row), _owner_name(right_row))}
    return {}


def _compare_rows(
    entity: str,
    key: str,
    left_row: object,
    right_row: object,
    derived: dict[str, tuple],
) -> list[PlanFieldDifference]:
    """Field-level diff of two matched rows (columns + derived values)."""
    differences: list[PlanFieldDifference] = []
    left_columns = left_row.__table__.columns.keys()  # type: ignore[attr-defined]
    for column in left_columns:
        if column in _SKIP_COLUMNS:
            continue
        left_value = getattr(left_row, column)
        right_value = getattr(right_row, column)
        if left_value != right_value:
            differences.append(
                PlanFieldDifference(
                    entity=entity,
                    key=key,
                    field=column,
                    left=_scalar(left_value),
                    right=_scalar(right_value),
                )
            )
    for field, (left_value, right_value) in derived.items():
        if left_value != right_value:
            differences.append(
                PlanFieldDifference(
                    entity=entity,
                    key=key,
                    field=field,
                    left=_scalar(left_value),
                    right=_scalar(right_value),
                )
            )
    return differences


def _side(plan: Plan) -> PlanSide:
    return PlanSide(
        id=plan.id,
        name=plan.name,
        is_baseline=plan.is_baseline,
        archived_at=plan.archived_at,
    )


def diff_plans(left: Plan, right: Plan) -> PlanComparison:
    """Field-level diff of two plans in the same household (spec §13).

    ``left``/``right`` identity flows into the report as ``left``/``right``
    values on every difference.  The caller guarantees the same household.
    """
    differences: list[PlanFieldDifference] = []
    for field in ("name", "is_baseline", "notes"):
        left_value = getattr(left, field)
        right_value = getattr(right, field)
        if left_value != right_value:
            differences.append(
                PlanFieldDifference(
                    entity="plan",
                    key="plan",
                    field=field,
                    left=_scalar(left_value),
                    right=_scalar(right_value),
                )
            )

    only_in_left: list[PlanEntityPresence] = []
    only_in_right: list[PlanEntityPresence] = []
    entity_rows = (
        ("person", left.people, right.people),
        ("account", left.accounts, right.accounts),
        ("liability", left.liabilities, right.liabilities),
        ("income_stream", left.income_streams, right.income_streams),
        ("expense", left.expenses, right.expenses),
    )
    for entity, left_rows, right_rows in entity_rows:
        matched, unmatched_left, unmatched_right = _pair_by_name(
            list(left_rows), list(right_rows)
        )
        only_in_left.extend(
            PlanEntityPresence(entity=entity, key=row.name) for row in unmatched_left
        )
        only_in_right.extend(
            PlanEntityPresence(entity=entity, key=row.name) for row in unmatched_right
        )
        for left_row, right_row in matched:
            differences.extend(
                _compare_rows(
                    entity,
                    left_row.name,
                    left_row,
                    right_row,
                    _derived_values(entity, left_row, right_row),
                )
            )

    return PlanComparison(
        left=_side(left),
        right=_side(right),
        differences=differences,
        only_in_left=only_in_left,
        only_in_right=only_in_right,
    )
