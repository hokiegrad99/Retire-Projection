"""Household endpoints, including plan collection under a household."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.db import DbSession
from app.models.people import Household, Plan
from app.schemas.finance import (
    HouseholdCreate,
    HouseholdPatch,
    HouseholdRead,
    PlanCreate,
    PlanRead,
)
from app.services.crud import create_and_commit, get_or_404, patch_and_commit

router = APIRouter(prefix="/api/households", tags=["households"])

DELETE_WARNING = (
    "Deleting removes this household and ALL of its plans and financial "
    "records. Re-send the request with ?confirm=true to proceed."
)


@router.get("", response_model=list[HouseholdRead])
def list_households(db: DbSession) -> list[Household]:
    return list(db.scalars(select(Household).order_by(Household.id)))


@router.post("", response_model=HouseholdRead, status_code=201)
def create_household(payload: HouseholdCreate, db: DbSession) -> Household:
    return create_and_commit(db, Household(**payload.model_dump()))


@router.get("/{household_id}", response_model=HouseholdRead)
def read_household(household_id: int, db: DbSession) -> Household:
    return get_or_404(db, Household, household_id, "household")


@router.patch("/{household_id}", response_model=HouseholdRead)
def update_household(
    household_id: int, payload: HouseholdPatch, db: DbSession
) -> Household:
    household = get_or_404(db, Household, household_id, "household")
    return patch_and_commit(db, household, payload, HouseholdCreate)


@router.delete("/{household_id}", status_code=204)
def delete_household(
    household_id: int,
    db: DbSession,
    confirm: bool = Query(False, description="Must be true to delete."),
) -> None:
    if not confirm:
        raise HTTPException(status_code=400, detail=DELETE_WARNING)
    household = get_or_404(db, Household, household_id, "household")
    db.delete(household)
    db.commit()


@router.get("/{household_id}/plans", response_model=list[PlanRead])
def list_plans(household_id: int, db: DbSession) -> list[Plan]:
    get_or_404(db, Household, household_id, "household")
    return list(
        db.scalars(select(Plan).where(Plan.household_id == household_id).order_by(Plan.id))
    )


@router.post("/{household_id}/plans", response_model=PlanRead, status_code=201)
def create_plan(
    household_id: int, payload: PlanCreate, db: DbSession
) -> Plan:
    get_or_404(db, Household, household_id, "household")
    if payload.is_baseline:
        existing = db.scalar(
            select(Plan.id).where(
                Plan.household_id == household_id, Plan.is_baseline.is_(True)
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
    if payload.parent_plan_id is not None:
        parent = get_or_404(db, Plan, payload.parent_plan_id, "plan")
        if parent.household_id != household_id:
            raise HTTPException(
                status_code=422, detail="parent plan belongs to a different household"
            )
    return create_and_commit(db, Plan(**payload.model_dump(), household_id=household_id))
