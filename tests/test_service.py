"""Tests of the service rules: normalization, validation and conversion helpers."""

import math

import pandas as pd
import pytest

from tests.conftest import failing
from world_bank_api.errors import InvalidRequestError, NotFoundError
from world_bank_api.service import (
    WorldBankService,
    clean_value,
    number_or_none,
    parse_code_list,
    parse_country_codes,
    period_argument,
    require_records,
    series_points,
    table_records,
    validate_frequency,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, "all"),
        ("", "all"),
        ("all", "all"),
        ("ALL", "all"),
        ("bra", "BRA"),
        (" BRA ", "BRA"),
        ("BRA,ARG", ["BRA", "ARG"]),
        ("bra, arg ,", ["BRA", "ARG"]),
        (",", "all"),
    ],
)
def test_parse_country_codes(raw, expected):
    assert parse_country_codes(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("NY.GDP.PCAP.CD", "NY.GDP.PCAP.CD"),
        ("NY.GDP.PCAP.CD, SP.POP.TOTL", ["NY.GDP.PCAP.CD", "SP.POP.TOTL"]),
    ],
)
def test_parse_code_list(raw, expected):
    assert parse_code_list(raw) == expected


@pytest.mark.parametrize("freq, expected", [("Y", "Y"), ("q", "Q"), (" m ", "M")])
def test_validate_frequency_accepts_the_three_frequencies(freq, expected):
    assert validate_frequency(freq) == expected


@pytest.mark.parametrize("freq", ["D", "W", "", "YY"])
def test_validate_frequency_rejects_anything_else(freq):
    with pytest.raises(InvalidRequestError):
        validate_frequency(freq)


def test_period_argument_without_dates_is_none():
    assert period_argument(None, None) is None


def test_period_argument_single_period():
    assert period_argument("2021", None) == "2021"


def test_period_argument_range():
    assert period_argument("2019", "2021") == ("2019", "2021")


def test_period_argument_end_without_start_is_rejected():
    with pytest.raises(InvalidRequestError, match="date_end needs date_start"):
        period_argument(None, "2021")


def test_number_or_none_converts_numbers_and_missing_values():
    assert number_or_none(3) == 3.0
    assert number_or_none("2.5") == 2.5
    assert number_or_none(None) is None
    assert number_or_none(float("nan")) is None
    assert number_or_none("not a number") is None


def test_clean_value_maps_nan_to_none_and_keeps_text():
    assert clean_value(float("nan")) is None
    assert clean_value(1.5) == 1.5
    assert clean_value("Brazil") == "Brazil"
    assert clean_value(None) is None
    assert clean_value(pd.Series([2.0]).iloc[0]) == 2.0


def test_series_points_pairs_each_period_with_its_value():
    series = pd.Series([1.5, float("nan")], index=["2021", "2022"])

    assert series_points(series) == [
        {"date": "2021", "value": 1.5},
        {"date": "2022", "value": None},
    ]


def test_table_records_moves_the_index_into_a_column():
    frame = pd.DataFrame({"gdp": [1.0, float("nan")]}, index=pd.Index(["2021", "2022"], name="date"))

    assert table_records(frame) == [
        {"date": "2021", "gdp": 1.0},
        {"date": "2022", "gdp": None},
    ]


def test_require_records_returns_non_empty_results():
    assert require_records([{"id": "BRA"}], "country") == [{"id": "BRA"}]


@pytest.mark.parametrize("empty", [None, [], pd.DataFrame()])
def test_require_records_raises_not_found_for_empty_results(empty):
    with pytest.raises(NotFoundError):
        require_records(empty, "country")


def test_service_rejects_a_table_without_indicators(gateway):
    service = WorldBankService(gateway)

    with pytest.raises(InvalidRequestError, match="At least one indicator"):
        service.get_table(indicators={}, country="all", date_start=None, date_end=None, freq="Y", source=None)
    assert gateway.calls == []


def test_service_validates_frequency_before_calling_the_gateway(gateway):
    service = WorldBankService(gateway)

    with pytest.raises(InvalidRequestError):
        service.get_observations(
            code="SP.POP.TOTL",
            country="all",
            date_start=None,
            date_end=None,
            freq="W",
            source=None,
            parse_dates=False,
        )
    assert gateway.calls == []


def test_service_get_country_normalizes_the_code(gateway):
    service = WorldBankService(gateway)

    service.get_country(" bra ")

    assert gateway.last_call()[1]["country_id"] == "BRA"


def test_service_get_indicator_returns_the_first_match(gateway):
    service = WorldBankService(gateway)

    assert service.get_indicator("NY.GDP.PCAP.CD")["id"] == "NY.GDP.PCAP.CD"


@pytest.mark.parametrize(
    "lookup, route",
    [
        (lambda service: service.get_source("99999"), "sources"),
        (lambda service: service.get_topic("99999"), "topics"),
        (lambda service: service.get_country("XXX"), "countries"),
        (lambda service: service.get_indicator("NOT.A.CODE"), "indicators"),
    ],
)
def test_lookup_of_an_invalid_id_is_not_found(gateway, lookup, route):
    gateway.responses[route] = failing(InvalidRequestError("Got error 120 (Invalid value)"))
    service = WorldBankService(gateway)

    with pytest.raises(NotFoundError, match="has the id or code"):
        lookup(service)


def test_list_with_an_invalid_filter_stays_a_bad_request(gateway):
    gateway.responses["sources"] = failing(InvalidRequestError("Got error 120 (Invalid value)"))
    service = WorldBankService(gateway)

    with pytest.raises(InvalidRequestError):
        service.list_sources("abc")
