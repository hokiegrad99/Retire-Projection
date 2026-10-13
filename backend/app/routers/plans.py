"""Plan endpoints: read, patch (incl. baseline promotion), guarded delete.

Plan *creation* lives under the household router
(``POST /api/households/{id}/plans``).
"""

from fastapi import APIRouter, HTTPException, Query

from app.db import DbSession
from app.models.people import Plan
from app.schemas.finance import PlanCreate, PlanPatch, PlanRead
from app.services.crud import get_or_404, patch_and_commit, promote_to_baseline

router = APIRouter(prefix="/api/plans", tags=["plans"])

DELETE_WARNING = (
    "Deleting a plan removes all of its people, accounts, income streams, "
    "expenses and liabilities. Re-send with ?confirm=true to proceed."
)


@router.get("/{plan_id}", response_model=PlanRead)
def read_plan(plan_id: int, db: DbSession) -> Plan:
    return get_or_404(db, Plan, plan_id, "plan")


@router.patch("/{plan_id}", response_model=PlanRead)
def update_plan(plan_id: int, payload: PlanPatch, db: DbSession) -> Plan:
    plan = get_or_404(db, Plan, plan_id, "plan")
    if "is_baseline" in payload.model_fields_set:
        if payload.is_baseline:
            promote_to_baseline(db, plan)  # demotes the current baseline
        else:
            plan.is_baseline = False
    if (
        payload.parent_plan_id is not None
        and payload.parent_plan_id != plan.parent_plan_id
    ):
        if payload.parent_plan_id == plan_id:
            raise HTTPException(status_code=422, detail="a plan cannot be its own parent")
        parent = get_or_404(db, Plan, payload.parent_plan_id, "plan")
        if parent.household_id != plan.household_id:
            raise HTTPException(
                status_code=422, detail="parent plan belongs to a different household"
            )
    return patch_and_commit(db, plan, payload, PlanCreate)


@router.delete("/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    db: DbSession,
    confirm: bool = Query(False, description="Must be true to delete a baseline."),
) -> None:
    plan = get_or_404(db, Plan, plan_id, "plan")
    if plan.is_baseline and not confirm:
        raise HTTPException(status_code=400, detail=DELETE_WARNING)
    db.delete(plan)
    db.commit()
