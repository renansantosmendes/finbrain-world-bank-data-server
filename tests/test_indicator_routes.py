"""Tests of the indicator routes: search and one indicator by code."""

from tests.conftest import upstream_failure


def test_search_without_filters_calls_the_gateway_with_none(client, gateway):
    response = client.get("/indicators")

    assert response.status_code == 200
    assert gateway.last_call() == (
        "indicators",
        {"indicator": None, "query": None, "source": None, "topic": None},
    )


def test_search_by_name_returns_matching_indicators(client, gateway):
    response = client.get("/indicators", params={"query": "gdp"})

    assert response.status_code == 200
    assert response.json()[0]["id"] == "NY.GDP.PCAP.CD"
    assert gateway.last_call()[1]["query"] == "gdp"


def test_search_by_codes_splits_the_list(client, gateway):
    client.get("/indicators", params={"indicator": "NY.GDP.PCAP.CD, SP.POP.TOTL"})

    assert gateway.last_call()[1]["indicator"] == ["NY.GDP.PCAP.CD", "SP.POP.TOTL"]


def test_search_by_source_and_topic_passes_both_filters(client, gateway):
    client.get("/indicators", params={"source": "2", "topic": "6"})

    assert gateway.last_call()[1] == {"indicator": None, "query": None, "source": "2", "topic": "6"}


def test_search_with_no_match_is_not_found(client, gateway):
    gateway.responses["indicators"] = []

    response = client.get("/indicators", params={"query": "zzz"})

    assert response.status_code == 404
    assert response.json()["message"] == "No indicator matches the request."


def test_get_indicator_returns_its_metadata(client, gateway):
    response = client.get("/indicators/NY.GDP.PCAP.CD")

    assert response.status_code == 200
    assert response.json()["name"] == "GDP per capita (current US$)"
    assert gateway.last_call() == (
        "indicators",
        {"indicator": "NY.GDP.PCAP.CD", "query": None, "source": None, "topic": None},
    )


def test_get_indicator_unknown_code_is_not_found(client, gateway):
    gateway.responses["indicators"] = []

    response = client.get("/indicators/NOT.A.CODE")

    assert response.status_code == 404


def test_indicator_routes_report_upstream_failure_as_bad_gateway(client, gateway):
    gateway.error = upstream_failure()

    assert client.get("/indicators").status_code == 502
    assert client.get("/indicators/NY.GDP.PCAP.CD").status_code == 502
