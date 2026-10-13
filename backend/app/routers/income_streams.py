"""Income stream endpoints (nested create/list under plans + item operations)."""

from fastapi import APIRouter
from sqlalchemy import select

from app.db import DbSession
from app.models.flows import IncomeStream
from app.models.people import Plan
from app.schemas.finance import IncomeStreamCreate, IncomeStreamPatch, IncomeStreamRead
from app.services.crud import (
    create_and_commit,
    delete_and_commit,
    ensure_person_in_plan,
    get_or_404,
    patch_and_commit,
)

router = APIRouter(tags=["income"])


@router.post(
    "/api/plans/{plan_id}/income-streams", response_model=IncomeStreamRead, status_code=201
)
def create_income_stream(
    plan_id: int, payload: IncomeStreamCreate, db: DbSession
) -> IncomeStream:
    get_or_404(db, Plan, plan_id, "plan")
    ensure_person_in_plan(db, plan_id, payload.owner_person_id)
    return create_and_commit(db, IncomeStream(**payload.model_dump(), plan_id=plan_id))


@router.get("/api/plans/{plan_id}/income-streams", response_model=list[IncomeStreamRead])
def list_income_streams(plan_id: int, db: DbSession) -> list[IncomeStream]:
    get_or_404(db, Plan, plan_id, "plan")
    return list(
        db.scalars(
            select(IncomeStream)
            .where(IncomeStream.plan_id == plan_id)
            .order_by(IncomeStream.id)
        )
    )


@router.get("/api/income-streams/{income_id}", response_model=IncomeStreamRead)
def read_income_stream(income_id: int, db: DbSession) -> IncomeStream:
    return get_or_404(db, IncomeStream, income_id, "income stream")


@router.patch("/api/income-streams/{income_id}", response_model=IncomeStreamRead)
def update_income_stream(
    income_id: int, payload: IncomeStreamPatch, db: DbSession
) -> IncomeStream:
    stream = get_or_404(db, IncomeStream, income_id, "income stream")
    if payload.owner_person_id is not None:
        ensure_person_in_plan(db, stream.plan_id, payload.owner_person_id)
    return patch_and_commit(db, stream, payload, IncomeStreamCreate)


@router.delete("/api/income-streams/{income_id}", status_code=204)
def delete_income_stream(income_id: int, db: DbSession) -> None:
    delete_and_commit(db, get_or_404(db, IncomeStream, income_id, "income stream"))
