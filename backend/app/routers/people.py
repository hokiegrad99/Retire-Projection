"""Person endpoints (nested create/list under plans + item operations)."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.db import DbSession
from app.models.people import Person, Plan
from app.schemas.finance import PersonCreate, PersonPatch, PersonRead
from app.services.crud import (
    create_and_commit,
    delete_and_commit,
    get_or_404,
    patch_and_commit,
    person_owns_accounts,
)

router = APIRouter(tags=["people"])


@router.post("/api/plans/{plan_id}/people", response_model=PersonRead, status_code=201)
def create_person(plan_id: int, payload: PersonCreate, db: DbSession) -> Person:
    get_or_404(db, Plan, plan_id, "plan")
    return create_and_commit(db, Person(**payload.model_dump(), plan_id=plan_id))


@router.get("/api/plans/{plan_id}/people", response_model=list[PersonRead])
def list_people(plan_id: int, db: DbSession) -> list[Person]:
    get_or_404(db, Plan, plan_id, "plan")
    return list(
        db.scalars(select(Person).where(Person.plan_id == plan_id).order_by(Person.id))
    )


@router.get("/api/people/{person_id}", response_model=PersonRead)
def read_person(person_id: int, db: DbSession) -> Person:
    return get_or_404(db, Person, person_id, "person")


@router.patch("/api/people/{person_id}", response_model=PersonRead)
def update_person(
    person_id: int, payload: PersonPatch, db: DbSession
) -> Person:
    person = get_or_404(db, Person, person_id, "person")
    return patch_and_commit(db, person, payload, PersonCreate)


@router.delete("/api/people/{person_id}", status_code=204)
def delete_person(person_id: int, db: DbSession) -> None:
    person = get_or_404(db, Person, person_id, "person")
    if person_owns_accounts(db, person_id):
        raise HTTPException(
            status_code=409,
            detail=(
                "person still owns accounts; delete or reassign them first "
                "(the database would otherwise remove them via cascade)"
            ),
        )
    delete_and_commit(db, person)
