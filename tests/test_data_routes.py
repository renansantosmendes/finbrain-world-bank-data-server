"""Tests of the data routes: observations, one series and the merged table."""

from tests.conftest import upstream_failure


def test_observations_default_to_every_country_and_yearly_frequency(client, gateway):
    response = client.get("/data/NY.GDP.PCAP.CD")

    assert response.status_code == 200
    assert gateway.last_call() == (
        "data",
        {
            "indicator": "NY.GDP.PCAP.CD",
            "country": "all",
            "date": None,
            "freq": "Y",
            "source": None,
            "parse_dates": False,
        },
    )


def test_observations_pass_the_period_range_and_filters(client, gateway):
    response = client.get(
        "/data/NY.GDP.PCAP.CD",
        params={"country": "BRA", "date_start": "2019", "date_end": "2021", "freq": "y", "source": 2, "parse_dates": True},
    )

    assert response.status_code == 200
    assert gateway.last_call() == (
        "data",
        {
            "indicator": "NY.GDP.PCAP.CD",
            "country": "BRA",
            "date": ("2019", "2021"),
            "freq": "Y",
            "source": 2,
            "parse_dates": True,
        },
    )


def test_observations_return_missing_values_as_null(client, gateway):
    response = client.get("/data/NY.GDP.PCAP.CD", params={"country": "BRA", "date_start": "2021"})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["value"] == 7972.54
    assert body[1]["value"] is None


def test_observations_with_a_single_period_send_one_value(client, gateway):
    client.get("/data/SP.POP.TOTL", params={"country": "BRA,ARG", "date_start": "2022"})

    assert gateway.last_call()[1]["country"] == ["BRA", "ARG"]
    assert gateway.last_call()[1]["date"] == "2022"


def test_observations_reject_an_end_without_a_start(client, gateway):
    response = client.get("/data/SP.POP.TOTL", params={"date_end": "2022"})

    assert response.status_code == 400
    assert response.json() == {"code": "invalid_request", "message": "date_end needs date_start."}
    assert gateway.calls == []


def test_observations_reject_an_unknown_frequency(client, gateway):
    response = client.get("/data/SP.POP.TOTL", params={"freq": "X"})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert gateway.calls == []


def test_observations_with_no_data_are_not_found(client, gateway):
    gateway.responses["data"] = []

    response = client.get("/data/SP.POP.TOTL", params={"country": "BRA"})

    assert response.status_code == 404
    assert response.json()["message"] == "No observation matches the request."


def test_series_returns_date_value_points(client, gateway):
    response = client.get("/series/SP.POP.TOTL", params={"country": "BRA", "date_start": "2021", "date_end": "2022"})

    assert response.status_code == 200
    assert response.json() == [
        {"date": "2021", "value": 7972.54},
        {"date": "2022", "value": None},
    ]
    assert gateway.last_call() == (
        "series",
        {"indicator": "SP.POP.TOTL", "country": "BRA", "date": ("2021", "2022"), "freq": "Y", "source": None},
    )


def test_series_rejects_an_unknown_frequency(client, gateway):
    response = client.get("/series/SP.POP.TOTL", params={"freq": "W"})

    assert response.status_code == 400
    assert gateway.calls == []


def test_series_with_no_points_is_not_found(client, gateway):
    import pandas as pd

    gateway.responses["series"] = pd.Series(dtype=float)

    response = client.get("/series/SP.POP.TOTL")

    assert response.status_code == 404


def test_table_merges_indicators_into_rows(client, gateway):
    response = client.post(
        "/data/table",
        json={
            "indicators": {"NY.GDP.PCAP.CD": "gdp_per_capita", "SP.POP.TOTL": "population"},
            "country": "BRA",
            "date_start": "2021",
            "date_end": "2022",
            "freq": "Y",
        },
    )

    assert response.status_code == 200
    assert response.json() == [
        {"date": "2021", "country": None, "gdp_per_capita": 7972.54, "population": 209550294.0},
        {"date": "2022", "country": None, "gdp_per_capita": None, "population": 210306415.0},
    ]
    name, arguments = gateway.last_call()
    assert name == "table"
    assert arguments["indicators"] == {"NY.GDP.PCAP.CD": "gdp_per_capita", "SP.POP.TOTL": "population"}
    assert arguments["country"] == "BRA"
    assert arguments["date"] == ("2021", "2022")


def test_table_defaults_to_every_country(client, gateway):
    client.post("/data/table", json={"indicators": {"SP.POP.TOTL": "population"}})

    assert gateway.last_call()[1]["country"] == "all"
    assert gateway.last_call()[1]["date"] is None


def test_table_requires_at_least_one_indicator(client, gateway):
    response = client.post("/data/table", json={"indicators": {}})

    assert response.status_code == 400
    assert response.json()["message"] == "At least one indicator is required."
    assert gateway.calls == []


def test_table_rejects_a_body_without_indicators(client, gateway):
    response = client.post("/data/table", json={"country": "BRA"})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert gateway.calls == []


def test_table_rejects_an_unknown_frequency(client, gateway):
    response = client.post(
        "/data/table",
        json={"indicators": {"SP.POP.TOTL": "population"}, "freq": "D"},
    )

    assert response.status_code == 400
    assert gateway.calls == []


def test_table_with_no_rows_is_not_found(client, gateway):
    import pandas as pd

    gateway.responses["table"] = pd.DataFrame()

    response = client.post("/data/table", json={"indicators": {"SP.POP.TOTL": "population"}})

    assert response.status_code == 404


def test_data_routes_report_upstream_failure_as_bad_gateway(client, gateway):
    gateway.error = upstream_failure()

    assert client.get("/data/SP.POP.TOTL").status_code == 502
    assert client.get("/series/SP.POP.TOTL").status_code == 502
    assert client.post("/data/table", json={"indicators": {"SP.POP.TOTL": "population"}}).status_code == 502
