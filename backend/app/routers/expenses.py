"""Expense endpoints (nested create/list under plans + item operations)."""

from fastapi import APIRouter
from sqlalchemy import select

from app.db import DbSession
from app.models.flows import Expense
from app.models.people import Plan
from app.schemas.finance import ExpenseCreate, ExpensePatch, ExpenseRead
from app.services.crud import (
    create_and_commit,
    delete_and_commit,
    get_or_404,
    patch_and_commit,
)

router = APIRouter(tags=["expenses"])


@router.post("/api/plans/{plan_id}/expenses", response_model=ExpenseRead, status_code=201)
def create_expense(
    plan_id: int, payload: ExpenseCreate, db: DbSession
) -> Expense:
    get_or_404(db, Plan, plan_id, "plan")
    return create_and_commit(db, Expense(**payload.model_dump(), plan_id=plan_id))


@router.get("/api/plans/{plan_id}/expenses", response_model=list[ExpenseRead])
def list_expenses(plan_id: int, db: DbSession) -> list[Expense]:
    get_or_404(db, Plan, plan_id, "plan")
    return list(
        db.scalars(select(Expense).where(Expense.plan_id == plan_id).order_by(Expense.id))
    )


@router.get("/api/expenses/{expense_id}", response_model=ExpenseRead)
def read_expense(expense_id: int, db: DbSession) -> Expense:
    return get_or_404(db, Expense, expense_id, "expense")


@router.patch("/api/expenses/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: int, payload: ExpensePatch, db: DbSession
) -> Expense:
    expense = get_or_404(db, Expense, expense_id, "expense")
    return patch_and_commit(db, expense, payload, ExpenseCreate)


@router.delete("/api/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: DbSession) -> None:
    delete_and_commit(db, get_or_404(db, Expense, expense_id, "expense"))
