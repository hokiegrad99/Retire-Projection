"""Plan endpoints: read, patch (incl. baseline promotion, archive), guarded
delete, duplication, and comparison (DATA-003).

Plan *creation* lives under the household router
(``POST /api/households/{id}/plans``).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from app.db import DbSession
from app.models.people import Plan
from app.schemas.finance import (
    PlanComparison,
    PlanCreate,
    PlanDuplicate,
    PlanPatch,
    PlanRead,
)
from app.services.crud import get_or_404, patch_and_commit, promote_to_baseline
from app.services.scenarios import copy_plan, diff_plans

router = APIRouter(prefix="/api/plans", tags=["plans"])

DELETE_WARNING = (
    "Deleting a plan removes all of its people, accounts, income streams, "
    "expenses and liabilities. Re-send with ?confirm=true to proceed."
)
BASELINE_ARCHIVED_WARNING = (
    "The baseline plan cannot be archived; promote another plan to baseline "
    "first (PATCH /api/plans/{id} {\"is_baseline\": true})."
)
PROMOTE_ARCHIVED_WARNING = (
    "An archived plan cannot be promoted to baseline; unarchive it first "
    "(PATCH {\"archived\": false})."
)


@router.get("/{plan_id}", response_model=PlanRead)
def read_plan(plan_id: int, db: DbSession) -> Plan:
    return get_or_404(db, Plan, plan_id, "plan")


@router.patch("/{plan_id}", response_model=PlanRead)
def update_plan(plan_id: int, payload: PlanPatch, db: DbSession) -> Plan:
    plan = get_or_404(db, Plan, plan_id, "plan")
    if "is_baseline" in payload.model_fields_set:
        if payload.is_baseline:
            if plan.archived_at is not None:
                raise HTTPException(status_code=409, detail=PROMOTE_ARCHIVED_WARNING)
            promote_to_baseline(db, plan)  # demotes the current baseline
        else:
            plan.is_baseline = False
    if "archived" in payload.model_fields_set and payload.archived is not None:
        if payload.archived:
            if plan.is_baseline:
                raise HTTPException(status_code=409, detail=BASELINE_ARCHIVED_WARNING)
            plan.archived_at = datetime.now(UTC)
        else:
            plan.archived_at = None
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


@router.post("/{plan_id}/duplicate", response_model=PlanRead, status_code=201)
def duplicate_plan(plan_id: int, payload: PlanDuplicate, db: DbSession) -> Plan:
    """Deep-copy a plan (people, accounts + allocations, liabilities,
    income streams, expenses) into a new scenario of the same household.

    Lineage: the copy's ``parent_plan_id`` points at the source.
    """
    source = get_or_404(db, Plan, plan_id, "plan")
    return copy_plan(db, source, payload)


@router.get("/{plan_id}/compare/{other_plan_id}", response_model=PlanComparison)
def compare_plans(plan_id: int, other_plan_id: int, db: DbSession) -> PlanComparison:
    """Field-level diff of two plans in the same household (spec §13):
    which entities differ, which exist on only one side.
    """
    left = get_or_404(db, Plan, plan_id, "plan")
    right = get_or_404(db, Plan, other_plan_id, "plan")
    if left.household_id != right.household_id:
        raise HTTPException(
            status_code=422, detail="plans belong to different households"
        )
    return diff_plans(left, right)
