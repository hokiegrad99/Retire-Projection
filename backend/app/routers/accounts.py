"""Account endpoints (nested create/list under plans + item operations).

Accounts are created through :class:`AccountDraft` (account + optional
allocation set, validated to sum to exactly 1). PATCH supports replacing
the whole allocation set; owner changes are validated against the plan.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import DbSession
from app.models.assets import Account, AccountAllocation
from app.models.people import Plan
from app.schemas.finance import (
    AccountCreate,
    AccountDraft,
    AccountPatch,
    AccountRead,
    validate_allocation_set,
)
from app.services.crud import (
    create_and_commit,
    delete_and_commit,
    ensure_person_in_plan,
    get_or_404,
    patch_and_commit,
)

router = APIRouter(tags=["accounts"])

_WITH_ALLOCATIONS = (selectinload(Account.allocations),)


def _allocations_from_payload(payload: AccountDraft) -> list[AccountAllocation]:
    return [
        AccountAllocation(asset_class=item.asset_class, weight=item.weight)
        for item in payload.allocations
    ]


@router.post("/api/plans/{plan_id}/accounts", response_model=AccountRead, status_code=201)
def create_account(
    plan_id: int, payload: AccountDraft, db: DbSession
) -> Account:
    get_or_404(db, Plan, plan_id, "plan")
    ensure_person_in_plan(db, plan_id, payload.account.owner_person_id)
    account = Account(**payload.account.model_dump(), plan_id=plan_id)
    account.allocations = _allocations_from_payload(payload)
    return create_and_commit(db, account)


@router.get("/api/plans/{plan_id}/accounts", response_model=list[AccountRead])
def list_accounts(plan_id: int, db: DbSession) -> list[Account]:
    get_or_404(db, Plan, plan_id, "plan")
    return list(
        db.scalars(
            select(Account)
            .where(Account.plan_id == plan_id)
            .options(*_WITH_ALLOCATIONS)
            .order_by(Account.id)
        )
    )


@router.get("/api/accounts/{account_id}", response_model=AccountRead)
def read_account(account_id: int, db: DbSession) -> Account:
    get_or_404(db, Account, account_id, "account")
    return db.scalar(
        select(Account).where(Account.id == account_id).options(*_WITH_ALLOCATIONS)
    )


@router.patch("/api/accounts/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int, payload: AccountPatch, db: DbSession
) -> Account:
    account = get_or_404(db, Account, account_id, "account")
    if payload.owner_person_id is not None:
        ensure_person_in_plan(db, account.plan_id, payload.owner_person_id)
    if "allocations" in payload.model_fields_set and payload.allocations is not None:
        # Schema-level sum/duplicate validation plus one shared rule set.
        try:
            validate_allocation_set(payload.allocations)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        # Replace in two phases: the unique (account_id, asset_class) constraint
        # would be violated if inserts were flushed before the old rows' deletes.
        account.allocations = []
        db.flush()  # phase 1: old rows deleted
        account.allocations = [
            AccountAllocation(asset_class=item.asset_class, weight=item.weight)
            for item in payload.allocations
        ]  # phase 2: new rows inserted on commit
    account = patch_and_commit(db, account, payload, AccountCreate)
    return db.scalar(
        select(Account).where(Account.id == account.id).options(*_WITH_ALLOCATIONS)
    )


@router.delete("/api/accounts/{account_id}", status_code=204)
def delete_account(account_id: int, db: DbSession) -> None:
    delete_and_commit(db, get_or_404(db, Account, account_id, "account"))
