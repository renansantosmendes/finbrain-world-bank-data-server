"""Tests of the catalogue routes: sources, topics, countries, income levels and lending types."""

from tests.conftest import failing, upstream_failure
from world_bank_api.errors import InvalidRequestError


def test_list_sources_returns_every_source(client, gateway):
    response = client.get("/sources")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["2", "1"]
    assert gateway.last_call() == ("sources", {"source_id": None})


def test_get_source_returns_the_requested_source(client, gateway):
    response = client.get("/sources/2")

    assert response.status_code == 200
    assert response.json()["code"] == "WDI"
    assert gateway.last_call() == ("sources", {"source_id": "2"})


def test_get_source_unknown_id_is_not_found(client, gateway):
    gateway.responses["sources"] = []

    response = client.get("/sources/999")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_list_topics_returns_every_topic(client, gateway):
    response = client.get("/topics")

    assert response.status_code == 200
    assert response.json()[0]["value"] == "Environment"
    assert gateway.last_call() == ("topics", {"topic_id": None})


def test_get_topic_returns_the_requested_topic(client, gateway):
    response = client.get("/topics/6")

    assert response.status_code == 200
    assert response.json()["id"] == "6"
    assert gateway.last_call() == ("topics", {"topic_id": "6"})


def test_get_topic_unknown_id_is_not_found(client, gateway):
    gateway.responses["topics"] = []

    response = client.get("/topics/999")

    assert response.status_code == 404


def test_list_countries_without_filters_returns_every_country(client, gateway):
    response = client.get("/countries")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["BRA", "ARG", "LCN"]
    assert gateway.last_call() == (
        "countries",
        {"country_id": None, "query": None, "incomelevel": None, "lendingtype": None},
    )


def test_list_countries_passes_every_filter_to_the_gateway(client, gateway):
    client.get("/countries", params={"query": "^Bra", "incomelevel": "LIC", "lendingtype": "IDX"})

    assert gateway.last_call() == (
        "countries",
        {"country_id": None, "query": "^Bra", "incomelevel": "LIC", "lendingtype": "IDX"},
    )


def test_list_countries_splits_several_codes(client, gateway):
    client.get("/countries", params={"country_id": "bra, arg"})

    assert gateway.last_call()[1]["country_id"] == ["BRA", "ARG"]


def test_list_countries_with_no_match_is_not_found(client, gateway):
    gateway.responses["countries"] = []

    response = client.get("/countries", params={"query": "^Zzz"})

    assert response.status_code == 404
    assert response.json()["message"] == "No country matches the request."


def test_get_country_returns_the_country(client, gateway):
    response = client.get("/countries/bra")

    assert response.status_code == 200
    assert response.json()["name"] == "Brazil"
    assert gateway.last_call()[1]["country_id"] == "BRA"


def test_get_country_unknown_code_is_not_found(client, gateway):
    gateway.responses["countries"] = []

    response = client.get("/countries/XXX")

    assert response.status_code == 404


def test_list_income_levels(client, gateway):
    response = client.get("/income-levels")

    assert response.status_code == 200
    assert response.json() == [{"id": "LIC", "iso2code": "XM", "value": "Low income"}]
    assert gateway.last_call() == ("income_levels", {})


def test_list_lending_types(client, gateway):
    response = client.get("/lending-types")

    assert response.status_code == 200
    assert response.json()[0]["value"] == "IDA"
    assert gateway.last_call() == ("lending_types", {})


def test_catalogue_routes_report_upstream_failure_as_bad_gateway(client, gateway):
    gateway.error = upstream_failure()

    for path in ("/sources", "/topics", "/countries", "/income-levels", "/lending-types"):
        response = client.get(path)
        assert response.status_code == 502, path
        assert response.json()["code"] == "upstream_unavailable", path



def test_get_source_with_an_invalid_id_is_not_found(client, gateway):
    gateway.responses["sources"] = failing(InvalidRequestError("Got error 120 (Invalid value)"))

    response = client.get("/sources/99999")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_list_countries_with_an_invalid_filter_is_a_bad_request(client, gateway):
    gateway.responses["countries"] = failing(InvalidRequestError("Got error 120 (Invalid value)"))

    response = client.get("/countries", params={"incomelevel": "NOPE"})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
