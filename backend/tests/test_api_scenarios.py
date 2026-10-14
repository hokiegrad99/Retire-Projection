"""End-to-end scenario management tests (DATA-003): duplicate, archive, compare.

Runs against the migrated `retirement_test` database through the FastAPI
TestClient; the autouse fixture truncates all domain tables after each test
(same isolation contract as ``test_api_crud.py``).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db import engine


@pytest.fixture(autouse=True)
def _clean_test_data(migrated_database: str):
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE household RESTART IDENTITY CASCADE"))


# --- builders ---------------------------------------------------------------


def _household(client, **overrides) -> dict:
    payload = {
        "name": "Scenario Household",
        "filing_status": "married_filing_jointly",
        "state_of_residence": "NJ",
    }
    payload.update(overrides)
    response = client.post("/api/households", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _plan(client, household_id: int, **overrides) -> dict:
    payload = {"name": "Baseline", "is_baseline": True}
    payload.update(overrides)
    response = client.post(f"/api/households/{household_id}/plans", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _person(client, plan_id: int, **overrides) -> dict:
    payload = {
        "name": "Alex",
        "role": "primary",
        "date_of_birth": "1980-05-01",
        "longevity_age": 90,
    }
    payload.update(overrides)
    response = client.post(f"/api/plans/{plan_id}/people", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _account(
    client, plan_id: int, owner_id: int, balance: str = "1000.00", **overrides
) -> dict:
    payload = {
        "account": {
            "owner_person_id": owner_id,
            "name": "Brokerage",
            "account_type": "taxable_brokerage",
            "tax_treatment": "taxable",
            "balance": balance,
        },
        "allocations": [
            {"asset_class": "us_stock", "weight": "0.6"},
            {"asset_class": "bonds", "weight": "0.4"},
        ],
    }
    payload.update(overrides)
    response = client.post(f"/api/plans/{plan_id}/accounts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _full_graph(client) -> dict:
    """A realistic plan graph touching every copyable entity type."""
    household = _household(client)
    baseline = _plan(client, household["id"])
    alex = _person(client, baseline["id"], name="Alex", role="primary")
    sam = _person(client, baseline["id"], name="Sam", role="spouse_partner")
    _account(client, baseline["id"], alex["id"], balance="1000.00")
    _account(
        client,
        baseline["id"],
        sam["id"],
        account={
            "owner_person_id": sam["id"],
            "name": "IRA",
            "account_type": "traditional_ira",
            "tax_treatment": "tax_deferred",
            "balance": "50000.00",
        },
        allocations=[
            {"asset_class": "bonds", "weight": "1"},
        ],
    )
    liability = client.post(
        f"/api/plans/{baseline['id']}/liabilities",
        json={
            "name": "Mortgage",
            "liability_type": "mortgage",
            "balance": "250000.00",
            "interest_rate": "0.055",
            "start_date": "2020-01-01",
            "payoff_date": "2040-01-01",
        },
    )
    assert liability.status_code == 201, liability.text
    income = client.post(
        f"/api/plans/{baseline['id']}/income-streams",
        json={
            "owner_person_id": alex["id"],
            "name": "Salary",
            "income_type": "salary",
            "amount": "8500.00",
            "frequency": "monthly",
            "start_date": "2026-01-01",
            "tax_classification": "ordinary",
        },
    )
    assert income.status_code == 201, income.text
    expense = client.post(
        f"/api/plans/{baseline['id']}/expenses",
        json={
            "name": "Groceries",
            "spending_class": "discretionary",
            "category": "food",
            "amount": "600.00",
            "start_date": "2026-01-01",
        },
    )
    assert expense.status_code == 201, expense.text
    return {
        "household": household,
        "baseline": baseline,
        "people": [alex, sam],
    }


def _list(client, plan_id: int, entity: str) -> list[dict]:
    response = client.get(f"/api/plans/{plan_id}/{entity}")
    assert response.status_code == 200, response.text
    return response.json()


def _allocations_by_plan(plan_id: int) -> dict:
    """{(account name, asset class): weight} for every allocation of a plan."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT a.name, al.asset_class, al.weight "
                "FROM account_allocation al JOIN account a ON al.account_id = a.id "
                "WHERE a.plan_id = :pid ORDER BY a.name, al.asset_class"
            ),
            {"pid": plan_id},
        )
    return {(name, asset_class): Decimal(str(weight)) for name, asset_class, weight in rows}


# --- duplication ------------------------------------------------------------


def test_duplicate_deep_copies_every_entity_and_leaves_source_intact(client) -> None:
    graph = _full_graph(client)
    source = graph["baseline"]

    duplicated = client.post(f"/api/plans/{source['id']}/duplicate", json={})
    assert duplicated.status_code == 201, duplicated.text
    copy = duplicated.json()

    # Name default, lineage, never a baseline, never archived.
    assert copy["name"] == "Baseline (copy)"
    assert copy["parent_plan_id"] == source["id"]
    assert copy["is_baseline"] is False
    assert copy["archived_at"] is None

    # Every owned entity was copied with identical counts.
    for entity in ("people", "accounts", "liabilities", "income-streams", "expenses"):
        source_rows = _list(client, source["id"], entity)
        copy_rows = _list(client, copy["id"], entity)
        assert len(copy_rows) == len(source_rows), entity
        assert {row["id"] for row in source_rows}.isdisjoint(
            {row["id"] for row in copy_rows}
        ), entity

    # Values (incl. Decimal precision) survive the copy.
    source_accounts = {row["name"]: row for row in _list(client, source["id"], "accounts")}
    copy_accounts = {row["name"]: row for row in _list(client, copy["id"], "accounts")}
    assert set(copy_accounts) == set(source_accounts)
    for name, row in copy_accounts.items():
        assert Decimal(str(row["balance"])) == Decimal(str(source_accounts[name]["balance"]))
        assert row["owner_person_id"] != source_accounts[name]["owner_person_id"]

    # Allocation rows are deep-copied with exact weights.
    assert _allocations_by_plan(source["id"]) == _allocations_by_plan(copy["id"])
    assert len(_allocations_by_plan(copy["id"])) == 3  # 2 + 1 rows

    # Owners were remapped to the *new* people of the copy.
    copy_people = {row["id"] for row in _list(client, copy["id"], "people")}
    for row in _list(client, copy["id"], "accounts") + _list(
        client, copy["id"], "income-streams"
    ):
        assert row["owner_person_id"] in copy_people

    # Source is untouched: still the single baseline, same rows and balances.
    plans = client.get(f"/api/households/{graph['household']['id']}/plans").json()
    baselines = [plan for plan in plans if plan["is_baseline"]]
    assert [plan["id"] for plan in baselines] == [source["id"]]
    assert len(_list(client, source["id"], "people")) == 2
    source_brokerage = next(
        row
        for row in _list(client, source["id"], "accounts")
        if row["name"] == "Brokerage"
    )
    assert Decimal(str(source_brokerage["balance"])) == Decimal("1000.00")


def test_editing_a_duplicate_never_touches_the_source(client) -> None:
    """Spec §13: mutating a scenario can never alter the baseline."""
    graph = _full_graph(client)
    source = graph["baseline"]
    copy = client.post(f"/api/plans/{source['id']}/duplicate", json={}).json()

    copy_account = _list(client, copy["id"], "accounts")[0]
    patched = client.patch(
        f"/api/accounts/{copy_account['id']}", json={"balance": "999999.99"}
    )
    assert patched.status_code == 200, patched.text
    renamed = client.patch(f"/api/plans/{copy['id']}", json={"name": "What if"})
    assert renamed.status_code == 200

    source_account = next(
        row
        for row in _list(client, source["id"], "accounts")
        if row["name"] == "Brokerage"
    )
    assert Decimal(str(source_account["balance"])) == Decimal("1000.00")
    assert client.get(f"/api/plans/{source['id']}").json()["name"] == "Baseline"


def test_duplicate_supports_rename_and_rejects_second_baseline(client) -> None:
    household = _household(client)
    baseline = _plan(client, household["id"])

    renamed = client.post(
        f"/api/plans/{baseline['id']}/duplicate",
        json={"name": "Retire at 55"},
    )
    assert renamed.status_code == 201, renamed.text
    assert renamed.json()["name"] == "Retire at 55"
    assert renamed.json()["parent_plan_id"] == baseline["id"]

    conflict = client.post(
        f"/api/plans/{baseline['id']}/duplicate", json={"is_baseline": True}
    )
    assert conflict.status_code == 409
    assert "already has a baseline" in conflict.text

    assert client.post("/api/plans/999/duplicate", json={}).status_code == 404


def test_duplicate_can_seed_the_first_baseline_of_a_household(client) -> None:
    household = _household(client)
    scenario = _plan(client, household["id"], name="Draft", is_baseline=False)

    seeded = client.post(
        f"/api/plans/{scenario['id']}/duplicate", json={"is_baseline": True}
    )
    assert seeded.status_code == 201, seeded.text
    assert seeded.json()["is_baseline"] is True
    assert seeded.json()["parent_plan_id"] == scenario["id"]


def test_rename_a_plan_via_patch(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])

    renamed = client.patch(f"/api/plans/{plan['id']}", json={"name": "Retire later"})
    assert renamed.status_code == 200
    assert client.get(f"/api/plans/{plan['id']}").json()["name"] == "Retire later"


# --- archive ----------------------------------------------------------------


def test_archived_plan_hides_from_default_listing_but_stays_readable(client) -> None:
    household = _household(client)
    baseline = _plan(client, household["id"])
    scenario = _plan(client, household["id"], name="Scenario", is_baseline=False)

    archived = client.patch(f"/api/plans/{scenario['id']}", json={"archived": True})
    assert archived.status_code == 200, archived.text
    assert archived.json()["archived_at"] is not None

    default = client.get(f"/api/households/{household['id']}/plans").json()
    assert [plan["id"] for plan in default] == [baseline["id"]]

    with_archived = client.get(
        f"/api/households/{household['id']}/plans", params={"include_archived": True}
    ).json()
    assert {plan["id"] for plan in with_archived} == {baseline["id"], scenario["id"]}

    # Still individually readable.
    read = client.get(f"/api/plans/{scenario['id']}")
    assert read.status_code == 200
    assert read.json()["archived_at"] is not None

    # Restore brings it back into the default listing.
    restored = client.patch(f"/api/plans/{scenario['id']}", json={"archived": False})
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    default_again = client.get(f"/api/households/{household['id']}/plans").json()
    assert len(default_again) == 2


def test_baseline_cannot_be_archived_and_archived_cannot_be_promoted(client) -> None:
    household = _household(client)
    baseline = _plan(client, household["id"])
    scenario = _plan(client, household["id"], name="Scenario", is_baseline=False)

    refused = client.patch(f"/api/plans/{baseline['id']}", json={"archived": True})
    assert refused.status_code == 409
    assert "baseline plan cannot be archived" in refused.text

    assert (
        client.patch(f"/api/plans/{scenario['id']}", json={"archived": True}).status_code
        == 200
    )
    promoted = client.patch(f"/api/plans/{scenario['id']}", json={"is_baseline": True})
    assert promoted.status_code == 409
    assert "unarchive it first" in promoted.text

    # Unblock: unarchive, then promote; the old baseline demotes.
    assert (
        client.patch(f"/api/plans/{scenario['id']}", json={"archived": False}).status_code
        == 200
    )
    promoted = client.patch(f"/api/plans/{scenario['id']}", json={"is_baseline": True})
    assert promoted.status_code == 200
    plans = client.get(f"/api/households/{household['id']}/plans").json()
    baselines = [plan for plan in plans if plan["is_baseline"]]
    assert [plan["id"] for plan in baselines] == [scenario["id"]]
    assert client.get(f"/api/plans/{baseline['id']}").json()["is_baseline"] is False
    assert len(plans) == 2


# --- comparison -------------------------------------------------------------


def test_compare_reports_field_diffs_and_presence(client) -> None:
    graph = _full_graph(client)
    baseline = graph["baseline"]
    copy = client.post(f"/api/plans/{baseline['id']}/duplicate", json={}).json()

    # Diverge one assumption: the copy's Brokerage balance.
    copy_account = next(
        row for row in _list(client, copy["id"], "accounts") if row["name"] == "Brokerage"
    )
    assert (
        client.patch(
            f"/api/accounts/{copy_account['id']}", json={"balance": "1500.00"}
        ).status_code
        == 200
    )
    # ...and add an expense that only exists in the copy.
    created = client.post(
        f"/api/plans/{copy['id']}/expenses",
        json={
            "name": "New Boat",
            "spending_class": "optional",
            "category": "travel",
            "amount": "40000.00",
            "start_date": "2027-01-01",
        },
    )
    assert created.status_code == 201, created.text

    response = client.get(f"/api/plans/{baseline['id']}/compare/{copy['id']}")
    assert response.status_code == 200, response.text
    report = response.json()

    assert report["left"]["id"] == baseline["id"]
    assert report["right"]["id"] == copy["id"]

    def diff(entity: str, key: str, field: str) -> dict:
        matches = [
            row
            for row in report["differences"]
            if row["entity"] == entity and row["key"] == key and row["field"] == field
        ]
        assert len(matches) == 1, (entity, key, field, report["differences"])
        return matches[0]

    # Metadata differences (renamed copy, scenario flag) are reported.
    name_diff = diff("plan", "plan", "name")
    assert name_diff["left"] == "Baseline"
    assert name_diff["right"] == "Baseline (copy)"
    assert diff("plan", "plan", "is_baseline")["right"] is False

    # The changed balance is reported field-level with normalized values.
    balance = diff("account", "Brokerage", "balance")
    assert balance["left"] == "1000.00"
    assert balance["right"] == "1500.00"

    # Untouched matched entities report no differences at all.
    untouched = [
        row
        for row in report["differences"]
        if row["entity"] in ("person", "liability", "income_stream")
    ]
    assert untouched == []

    # Presence: the boat exists only on the right; nothing only on the left.
    assert report["only_in_left"] == []
    assert {"entity": "expense", "key": "New Boat"} in report["only_in_right"]

    # Comparing a plan with itself reports an empty diff.
    same = client.get(f"/api/plans/{baseline['id']}/compare/{baseline['id']}").json()
    assert same["differences"] == []
    assert same["only_in_left"] == []
    assert same["only_in_right"] == []


def test_compare_owner_and_allocation_differences_are_reported(client) -> None:
    household = _household(client)
    baseline = _plan(client, household["id"])
    alex = _person(client, baseline["id"], name="Alex")
    _person(client, baseline["id"], name="Sam", role="spouse_partner")
    _account(client, baseline["id"], alex["id"])
    copy = client.post(f"/api/plans/{baseline['id']}/duplicate", json={}).json()

    # Move the copy's Brokerage to the copy's other person and rebalance it.
    copy_account = _list(client, copy["id"], "accounts")[0]
    copy_people = _list(client, copy["id"], "people")
    copy_sam = next(row for row in copy_people if row["name"] == "Sam")
    assert (
        client.patch(
            f"/api/accounts/{copy_account['id']}",
            json={
                "owner_person_id": copy_sam["id"],
                "allocations": [
                    {"asset_class": "bonds", "weight": "0.25"},
                    {"asset_class": "us_stock", "weight": "0.75"},
                ],
            },
        ).status_code
        == 200
    )

    report = client.get(
        f"/api/plans/{baseline['id']}/compare/{copy['id']}"
    ).json()
    fields = {
        (row["entity"], row["key"], row["field"]): row
        for row in report["differences"]
    }
    owner = fields[("account", "Brokerage", "owner")]
    assert (owner["left"], owner["right"]) == ("Alex", "Sam")
    allocations = fields[("account", "Brokerage", "allocations")]
    assert allocations["left"] == "bonds=0.400000, us_stock=0.600000"
    assert allocations["right"] == "bonds=0.250000, us_stock=0.750000"


def test_compare_requires_known_plans_of_one_household(client) -> None:
    household_a = _household(client, name="A")
    plan_a = _plan(client, household_a["id"])
    household_b = _household(client, name="B")
    plan_b = _plan(client, household_b["id"], name="Other")

    mismatch = client.get(f"/api/plans/{plan_a['id']}/compare/{plan_b['id']}")
    assert mismatch.status_code == 422
    assert "different households" in mismatch.text

    assert client.get(f"/api/plans/999/compare/{plan_a['id']}").status_code == 404
    assert client.get(f"/api/plans/{plan_a['id']}/compare/999").status_code == 404


# --- API surface ------------------------------------------------------------


def test_openapi_documents_scenario_endpoints(client) -> None:
    schema = client.get("/api/openapi.json").json()
    assert "/api/plans/{plan_id}/duplicate" in schema["paths"]
    assert "/api/plans/{plan_id}/compare/{other_plan_id}" in schema["paths"]
