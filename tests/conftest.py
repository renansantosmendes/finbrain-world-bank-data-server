"""Shared fixtures: a fake gateway and a test client that never reaches the network.

Route tests replace the service's gateway with ``FakeGateway``. Each test can
change what the fake returns or make it fail, and inspect the calls it received.
"""

from typing import Any, Callable, Union

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from world_bank_api.dependencies import get_service
from world_bank_api.errors import UpstreamUnavailableError
from world_bank_api.main import app
from world_bank_api.service import WorldBankService

SOURCE_WDI = {
    "id": "2",
    "name": "World Development Indicators",
    "code": "WDI",
    "lastupdated": "2026-10-08",
    "description": "",
    "url": "",
}
SOURCE_DOING_BUSINESS = {"id": "1", "name": "Doing Business", "code": "DBS", "lastupdated": "2021-08-18"}
TOPIC_ENVIRONMENT = {"id": "6", "value": "Environment", "sourceNote": "Natural resources."}
BRAZIL = {
    "id": "BRA",
    "iso2Code": "BR",
    "name": "Brazil",
    "region": {"id": "LCN", "iso2code": "ZJ", "value": "Latin America & Caribbean"},
    "incomeLevel": {"id": "UMC", "iso2code": "XT", "value": "Upper middle income"},
    "lendingType": {"id": "IBD", "iso2code": "XF", "value": "IBRD"},
    "capitalCity": "Brasilia",
}
ARGENTINA = {
    "id": "ARG",
    "iso2Code": "AR",
    "name": "Argentina",
    "region": {"id": "LCN", "iso2code": "ZJ", "value": "Latin America & Caribbean"},
}
LATIN_AMERICA = {
    "id": "LCN",
    "iso2Code": "ZJ",
    "name": "Latin America & Caribbean",
    "region": {"id": "NA", "iso2code": "NA", "value": "Aggregates"},
}
LOW_INCOME = {"id": "LIC", "iso2code": "XM", "value": "Low income"}
IDA = {"id": "IDX", "iso2code": "XI", "value": "IDA"}
GDP_PER_CAPITA = {
    "id": "NY.GDP.PCAP.CD",
    "name": "GDP per capita (current US$)",
    "unit": "",
    "source": {"id": "2", "value": "World Development Indicators"},
    "sourceNote": "GDP per capita is gross domestic product divided by midyear population.",
    "topics": [{"id": "19", "value": "Climate Change"}],
}
OBSERVATION_2021 = {
    "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita (current US$)"},
    "country": {"id": "BR", "value": "Brazil"},
    "countryiso3code": "BRA",
    "date": "2021",
    "value": 7972.54,
    "unit": "",
    "obs_status": "",
    "decimal": 1,
}
OBSERVATION_MISSING = {**OBSERVATION_2021, "date": "2022", "value": None}


def _select_by_id(records: list[dict[str, Any]], wanted: Any) -> list[dict[str, Any]]:
    """Keep the records whose ``id`` matches the wanted id, or all of them when none is wanted.

    Parameters
    ----------
    records : list[dict[str, Any]]
        Records to filter.
    wanted : Any
        Id to keep, or None.

    Returns
    -------
    list[dict[str, Any]]
        Matching records.
    """
    if wanted is None:
        return list(records)
    wanted_text = str(wanted)
    return [record for record in records if str(record.get("id")) == wanted_text]


def default_responses() -> dict[str, Any]:
    """Build the canned answers of the fake gateway.

    Returns
    -------
    dict[str, Any]
        Method name mapped to its answer, or to a function that computes it
        from the call arguments.
    """
    return {
        "sources": lambda source_id=None: _select_by_id(
            [SOURCE_WDI, SOURCE_DOING_BUSINESS], source_id
        ),
        "topics": lambda topic_id=None: _select_by_id([TOPIC_ENVIRONMENT], topic_id),
        "countries": [BRAZIL, ARGENTINA, LATIN_AMERICA],
        "income_levels": [LOW_INCOME],
        "lending_types": [IDA],
        "indicators": [GDP_PER_CAPITA],
        "data": [OBSERVATION_2021, OBSERVATION_MISSING],
        "series": pd.Series(
            [7972.54, None],
            index=["2021", "2022"],
            name="value",
        ),
        "table": pd.DataFrame(
            {"gdp_per_capita": [7972.54, None], "population": [209550294.0, 210306415.0]},
            index=pd.Index(["2021", "2022"], name="date"),
        ),
    }


class FakeGateway:
    """Stand-in for ``WorldBankGateway`` that records calls and returns canned data.

    Attributes
    ----------
    calls : list[tuple[str, dict[str, Any]]]
        Method name and keyword arguments of every call, in order.
    responses : dict[str, Any]
        Canned answer per method; a callable receives the call arguments.
    error : Optional[Exception]
        When set, every call raises it instead of answering.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.responses = default_responses()
        self.error: Union[Exception, None] = None

    def _respond(self, name: str, **kwargs: Any) -> Any:
        """Record one call and return its canned answer.

        Parameters
        ----------
        name : str
            Gateway method that was called.
        **kwargs : Any
            Arguments of the call.

        Returns
        -------
        Any
            The canned answer.

        Raises
        ------
        Exception
            The configured error, when one is set.
        """
        self.calls.append((name, kwargs))
        if self.error is not None:
            raise self.error
        answer = self.responses[name]
        if callable(answer):
            return answer(**kwargs)
        if isinstance(answer, list):
            return list(answer)
        return answer

    def sources(self, source_id: Any = None) -> Any:
        """Record a sources call."""
        return self._respond("sources", source_id=source_id)

    def topics(self, topic_id: Any = None) -> Any:
        """Record a topics call."""
        return self._respond("topics", topic_id=topic_id)

    def countries(self, country_id: Any = None, query: Any = None, incomelevel: Any = None, lendingtype: Any = None) -> Any:
        """Record a countries call."""
        return self._respond(
            "countries",
            country_id=country_id,
            query=query,
            incomelevel=incomelevel,
            lendingtype=lendingtype,
        )

    def income_levels(self) -> Any:
        """Record an income levels call."""
        return self._respond("income_levels")

    def lending_types(self) -> Any:
        """Record a lending types call."""
        return self._respond("lending_types")

    def indicators(self, indicator: Any = None, query: Any = None, source: Any = None, topic: Any = None) -> Any:
        """Record an indicators call."""
        return self._respond("indicators", indicator=indicator, query=query, source=source, topic=topic)

    def data(self, indicator: str, country: Any, date: Any, freq: str, source: Any, parse_dates: bool) -> Any:
        """Record a data call."""
        return self._respond(
            "data",
            indicator=indicator,
            country=country,
            date=date,
            freq=freq,
            source=source,
            parse_dates=parse_dates,
        )

    def series(self, indicator: str, country: Any, date: Any, freq: str, source: Any) -> Any:
        """Record a series call."""
        return self._respond("series", indicator=indicator, country=country, date=date, freq=freq, source=source)

    def table(self, indicators: dict[str, str], country: Any, date: Any, freq: str, source: Any) -> Any:
        """Record a table call."""
        return self._respond("table", indicators=indicators, country=country, date=date, freq=freq, source=source)

    def last_call(self) -> tuple[str, dict[str, Any]]:
        """Return the most recent call.

        Returns
        -------
        tuple[str, dict[str, Any]]
            Method name and keyword arguments of the last call.
        """
        return self.calls[-1]


@pytest.fixture
def gateway() -> FakeGateway:
    """Provide a fresh fake gateway for one test.

    Returns
    -------
    FakeGateway
        Gateway with the default canned answers.
    """
    return FakeGateway()


@pytest.fixture
def client(gateway: FakeGateway) -> TestClient:
    """Provide a test client whose service is backed by the fake gateway.

    Parameters
    ----------
    gateway : FakeGateway
        Fake gateway injected into the service.

    Yields
    ------
    TestClient
        Client for the application, with dependency overrides removed afterwards.
    """
    app.dependency_overrides[get_service] = lambda: WorldBankService(gateway)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def failing(error: Exception) -> Callable[..., Any]:
    """Build a canned answer that always raises the given error.

    Parameters
    ----------
    error : Exception
        Error to raise.

    Returns
    -------
    Callable[..., Any]
        Function that raises ``error`` on every call.
    """

    def raise_error(**kwargs: Any) -> Any:
        raise error

    return raise_error


def upstream_failure() -> UpstreamUnavailableError:
    """Build the error the gateway raises when the World Bank API cannot be reached.

    Returns
    -------
    UpstreamUnavailableError
        The application error for a network failure.
    """
    return UpstreamUnavailableError("The World Bank API could not be reached.")
