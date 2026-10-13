"""Liability endpoints (nested create/list under plans + item operations)."""

from fastapi import APIRouter
from sqlalchemy import select

from app.db import DbSession
from app.models.assets import Liability
from app.models.people import Plan
from app.schemas.finance import LiabilityCreate, LiabilityPatch, LiabilityRead
from app.services.crud import (
    create_and_commit,
    delete_and_commit,
    get_or_404,
    patch_and_commit,
)

router = APIRouter(tags=["liabilities"])


@router.post("/api/plans/{plan_id}/liabilities", response_model=LiabilityRead, status_code=201)
def create_liability(
    plan_id: int, payload: LiabilityCreate, db: DbSession
) -> Liability:
    get_or_404(db, Plan, plan_id, "plan")
    return create_and_commit(db, Liability(**payload.model_dump(), plan_id=plan_id))


@router.get("/api/plans/{plan_id}/liabilities", response_model=list[LiabilityRead])
def list_liabilities(plan_id: int, db: DbSession) -> list[Liability]:
    get_or_404(db, Plan, plan_id, "plan")
    return list(
        db.scalars(
            select(Liability).where(Liability.plan_id == plan_id).order_by(Liability.id)
        )
    )


@router.get("/api/liabilities/{liability_id}", response_model=LiabilityRead)
def read_liability(liability_id: int, db: DbSession) -> Liability:
    return get_or_404(db, Liability, liability_id, "liability")


@router.patch("/api/liabilities/{liability_id}", response_model=LiabilityRead)
def update_liability(
    liability_id: int, payload: LiabilityPatch, db: DbSession
) -> Liability:
    liability = get_or_404(db, Liability, liability_id, "liability")
    return patch_and_commit(db, liability, payload, LiabilityCreate)


@router.delete("/api/liabilities/{liability_id}", status_code=204)
def delete_liability(liability_id: int, db: DbSession) -> None:
    delete_and_commit(db, get_or_404(db, Liability, liability_id, "liability"))
