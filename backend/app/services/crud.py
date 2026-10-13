"""Shared service helpers for the CRUD API (DATA-002).

Design notes:

* ``apply_patch`` re-validates the **merged** record with the entity's
  ``*Create`` schema, so a PATCH can never produce a state that a POST would
  have rejected (one source of truth for cross-field rules).
* Explicit ``null`` clears an optional field; omitted fields keep their
  value (``model_fields_set`` distinguishes them).
* HTTPException carries API-level semantics; routers stay thin.
"""

from __future__ import annotations

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assets import Account
from app.models.people import Person, Plan


def get_or_404[ModelT: object](
    db: Session, model: type[ModelT], object_id: int, label: str
) -> ModelT:
    """Fetch a row by primary key or raise a 404 with a useful label."""
    obj = db.get(model, object_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} {object_id} not found")
    return obj


def create_and_commit[ModelT: object](db: Session, obj: ModelT) -> ModelT:
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def apply_patch(obj: object, patch: BaseModel, create_schema: type[BaseModel]) -> object:
    """Apply a PATCH to ``obj`` after re-validating the merged record."""
    data = {
        name: getattr(obj, name) for name in create_schema.model_fields if hasattr(obj, name)
    }
    for name in patch.model_fields_set:
        if name in create_schema.model_fields:
            data[name] = getattr(patch, name)
    try:
        validated = create_schema.model_validate(data)
    except ValidationError as exc:
        # Merged-state violations are client errors, not 500s: surface them
        # in the same shape FastAPI uses for body validation errors.
        raise HTTPException(
            status_code=422,
            detail=exc.errors(include_url=False, include_context=False, include_input=False),
        ) from exc
    for name in create_schema.model_fields:
        if hasattr(validated, name):
            setattr(obj, name, getattr(validated, name))
    return obj


def patch_and_commit[ModelT: object](
    db: Session, obj: ModelT, patch: BaseModel, create_schema: type[BaseModel]
) -> ModelT:
    apply_patch(obj, patch, create_schema)
    db.commit()
    db.refresh(obj)
    return obj


def delete_and_commit(db: Session, obj: object) -> None:
    db.delete(obj)
    db.commit()


def ensure_person_in_plan(
    db: Session, plan_id: int, person_id: int, label: str = "owner"
) -> Person:
    """Referential guard: a person referenced by a cash-flow row must belong
    to the same plan, otherwise the graph would span plans and break
    scenario isolation."""
    person = get_or_404(db, Person, person_id, "person")
    if person.plan_id != plan_id:
        raise HTTPException(
            status_code=422,
            detail=f"{label} person {person_id} does not belong to plan {plan_id}",
        )
    return person


def person_owns_accounts(db: Session, person_id: int) -> bool:
    count = db.scalar(
        select(Account.id).where(Account.owner_person_id == person_id).limit(1)
    )
    return count is not None


def promote_to_baseline(db: Session, plan: Plan) -> None:
    """Make ``plan`` the household's baseline, demoting any current one.

    Lineage (``parent_plan_id``) is intentionally preserved so the promoted
    plan still shows where it came from (DECISIONS D-011).
    """
    if plan.is_baseline:
        return
    current = db.scalar(
        select(Plan).where(
            Plan.household_id == plan.household_id,
            Plan.is_baseline.is_(True),
            Plan.id != plan.id,
        )
    )
    if current is not None:
        current.is_baseline = False
    plan.is_baseline = True
