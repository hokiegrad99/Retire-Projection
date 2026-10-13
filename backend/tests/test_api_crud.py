"""End-to-end API tests for the CRUD layer (DATA-002).

Every test runs against the migrated `retirement_test` database via the
FastAPI TestClient (the app's own engine binds to it). The autouse fixture
truncates all domain tables after each test, so tests are independent.
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
        "name": "Demo Household",
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


def _account(client, plan_id: int, owner_id: int, balance: str = "1000.00", **overrides) -> dict:
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


# --- households --------------------------------------------------------------


def test_household_crud_roundtrip(client) -> None:
    created = _household(client)
    assert created["state_of_residence"] == "NJ"
    assert created["filing_status"] == "married_filing_jointly"

    listing = client.get("/api/households")
    assert listing.status_code == 200 and len(listing.json()) == 1

    patched = client.patch(
        f"/api/households/{created['id']}", json={"name": "Renamed Household"}
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Renamed Household"

    assert client.get(f"/api/households/{created['id']}").json()["name"] == "Renamed Household"


def test_household_validation_reaches_the_client(client) -> None:
    bad_state = client.post(
        "/api/households",
        json={"name": "X", "filing_status": "single", "state_of_residence": "NEWJERSEY"},
    )
    assert bad_state.status_code == 422
    assert "state_of_residence" in bad_state.text

    bad_enum = client.post(
        "/api/households", json={"name": "X", "filing_status": "not_a_status"}
    )
    assert bad_enum.status_code == 422

    unknown_field = client.post(
        "/api/households", json={"name": "X", "filing_status": "single", "ssn": "nope"}
    )
    assert unknown_field.status_code == 422


def test_household_delete_requires_confirmation(client) -> None:
    created = _household(client)
    refused = client.delete(f"/api/households/{created['id']}")
    assert refused.status_code == 400
    assert "confirm=true" in refused.json()["detail"]

    ok = client.delete(f"/api/households/{created['id']}?confirm=true")
    assert ok.status_code == 204
    assert client.get(f"/api/households/{created['id']}").status_code == 404


def test_missing_resources_return_404(client) -> None:
    assert client.get("/api/households/999").status_code == 404
    assert client.get("/api/plans/999").status_code == 404
    assert client.get("/api/people/999").status_code == 404
    assert client.get("/api/accounts/999").status_code == 404
    assert client.get("/api/liabilities/999").status_code == 404
    assert client.get("/api/income-streams/999").status_code == 404
    assert client.get("/api/expenses/999").status_code == 404


# --- plans, baselines, promotion ---------------------------------------------


def test_plan_create_list_get_patch(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    assert plan["is_baseline"] is True

    listing = client.get(f"/api/households/{household['id']}/plans")
    assert listing.status_code == 200 and len(listing.json()) == 1

    patched = client.patch(f"/api/plans/{plan['id']}", json={"name": "Baseline v2"})
    assert patched.status_code == 200 and patched.json()["name"] == "Baseline v2"


def test_second_baseline_is_rejected_with_409(client) -> None:
    household = _household(client)
    _plan(client, household["id"])
    conflict = client.post(
        f"/api/households/{household['id']}/plans",
        json={"name": "Pretender", "is_baseline": True},
    )
    assert conflict.status_code == 409
    assert "baseline" in conflict.json()["detail"]


def test_promotion_demotes_old_baseline_and_keeps_lineage(client) -> None:
    household = _household(client)
    baseline = _plan(client, household["id"])
    scenario = _plan(
        client,
        household["id"],
        name="Retire early",
        is_baseline=False,
        parent_plan_id=baseline["id"],
    )

    promoted = client.patch(f"/api/plans/{scenario['id']}", json={"is_baseline": True})
    assert promoted.status_code == 200
    assert promoted.json()["is_baseline"] is True
    # lineage preserved on the promoted plan (DECISIONS D-011)
    assert promoted.json()["parent_plan_id"] == baseline["id"]

    old = client.get(f"/api/plans/{baseline['id']}").json()
    assert old["is_baseline"] is False


def test_baseline_delete_requires_confirmation_but_scenarios_do_not(client) -> None:
    household = _household(client)
    baseline = _plan(client, household["id"])
    scenario = _plan(client, household["id"], name="What-if", is_baseline=False)

    refused = client.delete(f"/api/plans/{baseline['id']}")
    assert refused.status_code == 400

    ok = client.delete(f"/api/plans/{scenario['id']}")
    assert ok.status_code == 204

    assert client.delete(f"/api/plans/{baseline['id']}?confirm=true").status_code == 204


def test_parent_plan_must_stay_within_the_household(client) -> None:
    household_a = _household(client, name="A")
    household_b = _household(client, name="B")
    plan_b = _plan(client, household_b["id"])
    response = client.post(
        f"/api/households/{household_a['id']}/plans",
        json={"name": "Cross-linked", "is_baseline": False, "parent_plan_id": plan_b["id"]},
    )
    assert response.status_code == 422


# --- people ------------------------------------------------------------------


def test_person_crud_roundtrip(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    person = _person(client, plan["id"])
    assert person["longevity_age"] == 90

    listing = client.get(f"/api/plans/{plan['id']}/people")
    assert listing.status_code == 200 and len(listing.json()) == 1

    patched = client.patch(f"/api/people/{person['id']}", json={"name": "Alexandra"})
    assert patched.status_code == 200 and patched.json()["name"] == "Alexandra"


def test_person_dependent_window_rejected_through_api(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    response = client.post(
        f"/api/plans/{plan['id']}/people",
        json={
            "name": "Kiddo",
            "role": "dependent",
            "date_of_birth": "2015-01-01",
            "dependent_from": "2030-01-01",
            "dependent_until": "2029-01-01",
        },
    )
    assert response.status_code == 422


def test_deleting_a_person_with_accounts_is_blocked(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    person = _person(client, plan["id"])
    _account(client, plan["id"], person["id"])

    blocked = client.delete(f"/api/people/{person['id']}")
    assert blocked.status_code == 409
    assert "accounts" in blocked.json()["detail"]

    account_id = client.get(f"/api/plans/{plan['id']}/accounts").json()[0]["id"]
    assert client.delete(f"/api/accounts/{account_id}").status_code == 204
    assert client.delete(f"/api/people/{person['id']}").status_code == 204


# --- accounts ----------------------------------------------------------------


def test_account_create_with_allocations(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    person = _person(client, plan["id"])
    account = _account(client, plan["id"], person["id"])

    assert Decimal(account["balance"]) == Decimal("1000.00")
    weights = {row["asset_class"]: Decimal(row["weight"]) for row in account["allocations"]}
    assert weights == {"us_stock": Decimal("0.600000"), "bonds": Decimal("0.400000")}

    fetched = client.get(f"/api/accounts/{account['id']}").json()
    assert len(fetched["allocations"]) == 2

    listing = client.get(f"/api/plans/{plan['id']}/accounts").json()
    assert len(listing) == 1


def test_account_allocation_sum_rejected(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    person = _person(client, plan["id"])
    response = client.post(
        f"/api/plans/{plan['id']}/accounts",
        json={
            "account": {
                "owner_person_id": person["id"],
                "name": "Half",
                "account_type": "checking",
                "tax_treatment": "taxable",
                "balance": "10.00",
            },
            "allocations": [{"asset_class": "us_stock", "weight": "0.5"}],
        },
    )
    assert response.status_code == 422
    assert "sum to exactly 1" in response.text


def test_account_owner_must_belong_to_the_plan(client) -> None:
    household = _household(client)
    plan_a = _plan(client, household["id"], name="A", is_baseline=True)
    plan_b = _plan(client, household["id"], name="B", is_baseline=False)
    outsider = _person(client, plan_b["id"])
    response = client.post(
        f"/api/plans/{plan_a['id']}/accounts",
        json={
            "account": {
                "owner_person_id": outsider["id"],
                "name": "Cross-plan",
                "account_type": "checking",
                "tax_treatment": "taxable",
                "balance": "10.00",
            }
        },
    )
    assert response.status_code == 422
    assert "does not belong to plan" in response.text


def test_account_patch_and_merged_validation(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    person = _person(client, plan["id"])
    account = _account(client, plan["id"], person["id"])

    patched = client.patch(
        f"/api/accounts/{account['id']}", json={"balance": "12000.50"}
    )
    assert patched.status_code == 200
    assert Decimal(patched.json()["balance"]) == Decimal("12000.50")

    rejected = client.patch(f"/api/accounts/{account['id']}", json={"balance": "-5"})
    assert rejected.status_code == 422


def test_account_patch_replaces_allocation_set(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    person = _person(client, plan["id"])
    account = _account(client, plan["id"], person["id"])

    patched = client.patch(
        f"/api/accounts/{account['id']}",
        json={"allocations": [{"asset_class": "us_stock", "weight": "1.0"}]},
    )
    assert patched.status_code == 200
    assert len(patched.json()["allocations"]) == 1
    assert patched.json()["allocations"][0]["asset_class"] == "us_stock"

    bad = client.patch(
        f"/api/accounts/{account['id']}",
        json={"allocations": [{"asset_class": "cash", "weight": "0.9"}]},
    )
    assert bad.status_code == 422


def test_nested_create_under_unknown_plan_404(client) -> None:
    response = client.post(
        "/api/plans/999/accounts",
        json={"account": {"owner_person_id": 1, "name": "x", "account_type": "checking",
                          "tax_treatment": "taxable", "balance": "1"}},
    )
    assert response.status_code == 404


# --- liabilities, income, expenses -------------------------------------------


def test_liability_crud_and_date_order_validation(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    created = client.post(
        f"/api/plans/{plan['id']}/liabilities",
        json={
            "name": "Mortgage",
            "liability_type": "mortgage",
            "balance": "250000.00",
            "interest_rate": "0.055",
            "start_date": "2020-01-01",
            "payoff_date": "2040-01-01",
        },
    )
    assert created.status_code == 201
    liability_id = created.json()["id"]

    bad = client.post(
        f"/api/plans/{plan['id']}/liabilities",
        json={"name": "Backwards", "liability_type": "auto", "balance": "100",
              "interest_rate": "0.01", "start_date": "2030-01-01", "payoff_date": "2029-01-01"},
    )
    assert bad.status_code == 422

    patched = client.patch(f"/api/liabilities/{liability_id}", json={"balance": "240000.00"})
    assert patched.status_code == 200
    assert client.delete(f"/api/liabilities/{liability_id}").status_code == 204


def test_income_crud_and_survivor_validation(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    person = _person(client, plan["id"])
    created = client.post(
        f"/api/plans/{plan['id']}/income-streams",
        json={
            "owner_person_id": person["id"],
            "name": "Salary",
            "income_type": "salary",
            "amount": "8500.00",
            "frequency": "monthly",
            "start_date": "2026-01-01",
            "tax_classification": "ordinary",
        },
    )
    assert created.status_code == 201
    stream_id = created.json()["id"]

    bad = client.post(
        f"/api/plans/{plan['id']}/income-streams",
        json={"owner_person_id": person["id"], "name": "Broken", "income_type": "pension",
              "amount": "100", "frequency": "annual", "start_date": "2026-01-01",
              "tax_classification": "ordinary", "survivor_percent": "0.5"},
    )
    assert bad.status_code == 422

    patched = client.patch(f"/api/income-streams/{stream_id}", json={"amount": "9000.00"})
    assert patched.status_code == 200
    assert Decimal(patched.json()["amount"]) == Decimal("9000.00")
    assert client.delete(f"/api/income-streams/{stream_id}").status_code == 204


def test_income_owner_change_is_plan_checked(client) -> None:
    household = _household(client)
    plan_a = _plan(client, household["id"], name="A", is_baseline=True)
    plan_b = _plan(client, household["id"], name="B", is_baseline=False)
    person_a = _person(client, plan_a["id"])
    person_b = _person(client, plan_b["id"])
    stream = client.post(
        f"/api/plans/{plan_a['id']}/income-streams",
        json={"owner_person_id": person_a["id"], "name": "Wages", "income_type": "salary",
              "amount": "100", "frequency": "monthly", "start_date": "2026-01-01",
              "tax_classification": "ordinary"},
    ).json()

    response = client.patch(
        f"/api/income-streams/{stream['id']}", json={"owner_person_id": person_b["id"]}
    )
    assert response.status_code == 422
    assert "does not belong to plan" in response.text


def test_expense_crud_applies_documented_defaults(client) -> None:
    household = _household(client)
    plan = _plan(client, household["id"])
    created = client.post(
        f"/api/plans/{plan['id']}/expenses",
        json={"name": "Groceries", "spending_class": "discretionary", "category": "food",
              "amount": "600.00", "start_date": "2026-01-01"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["frequency"] == "monthly"
    assert body["basis"] == "nominal"
    assert body["phase"] == "any_time"
    expense_id = body["id"]

    bad = client.post(
        f"/api/plans/{plan['id']}/expenses",
        json={"name": "Mystery", "spending_class": "optional", "category": "other",
              "amount": "10.00", "start_date": "2026-01-01"},
    )
    assert bad.status_code == 422
    assert "category_detail" in bad.text

    assert client.delete(f"/api/expenses/{expense_id}").status_code == 204


def test_expense_patch_revalidates_the_merged_record(client) -> None:
    """A PATCH that is individually valid but invalid in combination must fail."""
    household = _household(client)
    plan = _plan(client, household["id"])
    expense = client.post(
        f"/api/plans/{plan['id']}/expenses",
        json={"name": "HOA", "spending_class": "essential", "category": "housing",
              "amount": "300.00", "start_date": "2026-01-01"},
    ).json()

    # adjustment_age alone breaks the both-or-neither rule on the merged row.
    response = client.patch(f"/api/expenses/{expense['id']}", json={"adjustment_age": 70})
    assert response.status_code == 422
    assert "set together" in response.text

    # Both together is fine.
    ok = client.patch(
        f"/api/expenses/{expense['id']}",
        json={"adjustment_age": 70, "adjustment_percent": "-0.25"},
    )
    assert ok.status_code == 200
    assert ok.json()["adjustment_age"] == 70


# --- scenario isolation invariant (spec §13) ----------------------------------


def test_editing_a_scenario_never_touches_the_baseline(client) -> None:
    household = _household(client)
    baseline = _plan(client, household["id"])
    scenario = _plan(
        client, household["id"], name="What-if", is_baseline=False, parent_plan_id=baseline["id"]
    )

    base_person = _person(client, baseline["id"], name="Base Alex")
    scen_person = _person(client, scenario["id"], name="Scenario Alex")
    base_account = _account(client, baseline["id"], base_person["id"], balance="1000.00")
    scen_account = _account(client, scenario["id"], scen_person["id"], balance="1000.00")

    patched = client.patch(
        f"/api/accounts/{scen_account['id']}", json={"balance": "9999.99"}
    )
    assert patched.status_code == 200

    base_after = client.get(f"/api/accounts/{base_account['id']}").json()
    scen_after = client.get(f"/api/accounts/{scen_account['id']}").json()
    assert Decimal(base_after["balance"]) == Decimal("1000.00")  # untouched
    assert Decimal(scen_after["balance"]) == Decimal("9999.99")

    # Lists are plan-scoped: each plan sees exactly its own account.
    assert len(client.get(f"/api/plans/{baseline['id']}/accounts").json()) == 1
    assert len(client.get(f"/api/plans/{scenario['id']}/accounts").json()) == 1

    # Deleting the scenario reclaims its rows only.
    assert client.delete(f"/api/plans/{scenario['id']}").status_code == 204
    assert client.get(f"/api/accounts/{base_account['id']}").status_code == 200


# --- API surface --------------------------------------------------------------


def test_openapi_documents_every_entity(client) -> None:
    schema = client.get("/api/openapi.json").json()
    paths = schema["paths"]
    for expected in (
        "/api/households",
        "/api/households/{household_id}/plans",
        "/api/plans/{plan_id}/people",
        "/api/plans/{plan_id}/accounts",
        "/api/plans/{plan_id}/liabilities",
        "/api/plans/{plan_id}/income-streams",
        "/api/plans/{plan_id}/expenses",
        "/api/accounts/{account_id}",
        "/api/expenses/{expense_id}",
    ):
        assert expected in paths, expected
