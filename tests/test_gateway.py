"""Tests of the gateway: no cache is kept, and library failures become application errors."""

import json
import os
import tempfile

import pytest
import requests
from wbdata import fetcher as wbdata_fetcher

from world_bank_api.errors import InvalidRequestError, NotFoundError, UpstreamUnavailableError
from world_bank_api.gateway import NoCache, UncachedClient, WorldBankGateway


def canned_page(rows: list[dict]) -> str:
    """Build the JSON body the World Bank API returns for one page of records.

    Parameters
    ----------
    rows : list[dict]
        Records of the page.

    Returns
    -------
    str
        JSON text in the API's ``[page information, records]`` layout.
    """
    page = {"page": 1, "pages": 1, "per_page": 1000, "total": len(rows), "sourceid": "2", "lastupdated": "2026-10-08"}
    return json.dumps([page, rows])


SOURCE_ROWS = [{"id": "2", "name": "World Development Indicators", "code": "WDI", "lastupdated": "2026-10-08"}]


def test_no_cache_never_keeps_anything():
    cache = NoCache()

    cache["key"] = "value"

    assert "key" not in cache
    assert len(cache) == 0
    assert list(cache) == []
    with pytest.raises(KeyError):
        cache["key"]


def test_no_cache_ignores_deletion_of_missing_keys():
    cache = NoCache()

    with pytest.raises(KeyError):
        del cache["missing"]


def test_uncached_client_uses_no_cache_in_its_fetcher():
    client = UncachedClient()

    assert isinstance(client.fetcher.cache, NoCache)


def test_uncached_client_fetches_again_on_every_call(monkeypatch):
    calls = []

    def fake_body(self, url, params):
        calls.append(url)
        return canned_page(SOURCE_ROWS)

    monkeypatch.setattr(wbdata_fetcher.Fetcher, "_get_response_body", fake_body)
    client = UncachedClient()

    first = client.get_sources(skip_cache=True)
    second = client.get_sources(skip_cache=True)

    assert len(calls) == 2
    assert first[0]["code"] == "WDI"
    assert second[0]["code"] == "WDI"


def test_uncached_client_writes_no_cache_file(monkeypatch):
    monkeypatch.setattr(wbdata_fetcher.Fetcher, "_get_response_body", lambda self, url, params: canned_page(SOURCE_ROWS))
    cache_directory = os.path.dirname(os.environ["WBDATA_CACHE_PATH"])

    def listing() -> set[str]:
        return set(os.listdir(cache_directory)) if os.path.isdir(cache_directory) else set()

    before = listing()
    UncachedClient().get_sources(skip_cache=True)

    assert listing() == before


def test_cache_location_is_moved_to_the_temporary_directory():
    expected_root = os.path.abspath(tempfile.gettempdir())

    assert os.path.abspath(os.environ["WBDATA_CACHE_PATH"]).startswith(expected_root)


class RecordingClient:
    """Client double that records the arguments of each call and can fail."""

    def __init__(self, error: Exception = None) -> None:
        self.error = error
        self.calls = []

    def _answer(self, name: str, **kwargs):
        self.calls.append((name, kwargs))
        if self.error is not None:
            raise self.error
        return [{"id": "ok"}]

    def get_sources(self, **kwargs):
        return self._answer("get_sources", **kwargs)

    def get_topics(self, **kwargs):
        return self._answer("get_topics", **kwargs)

    def get_countries(self, **kwargs):
        return self._answer("get_countries", **kwargs)

    def get_incomelevels(self, **kwargs):
        return self._answer("get_incomelevels", **kwargs)

    def get_lendingtypes(self, **kwargs):
        return self._answer("get_lendingtypes", **kwargs)

    def get_indicators(self, **kwargs):
        return self._answer("get_indicators", **kwargs)

    def get_data(self, **kwargs):
        return self._answer("get_data", **kwargs)

    def get_series(self, **kwargs):
        return self._answer("get_series", **kwargs)

    def get_dataframe(self, **kwargs):
        return self._answer("get_dataframe", **kwargs)


@pytest.mark.parametrize(
    "call",
    [
        lambda gateway: gateway.sources("2"),
        lambda gateway: gateway.topics("6"),
        lambda gateway: gateway.countries("BRA", "^Bra", "LIC", "IDX"),
        lambda gateway: gateway.income_levels(),
        lambda gateway: gateway.lending_types(),
        lambda gateway: gateway.indicators("NY.GDP.PCAP.CD"),
        lambda gateway: gateway.data("NY.GDP.PCAP.CD", "BRA", "2021", "Y", 2, False),
        lambda gateway: gateway.series("SP.POP.TOTL", "BRA", ("2020", "2021"), "Y", None),
        lambda gateway: gateway.table({"SP.POP.TOTL": "population"}, "all", None, "Y", None),
    ],
)
def test_every_gateway_call_asks_the_client_to_skip_the_cache(call):
    client = RecordingClient()
    gateway = WorldBankGateway(client)

    call(gateway)

    assert client.calls, "the gateway should call the client"
    for name, kwargs in client.calls:
        assert kwargs.get("skip_cache") is True, name


def test_gateway_forwards_the_arguments_unchanged():
    client = RecordingClient()
    gateway = WorldBankGateway(client)

    gateway.data("NY.GDP.PCAP.CD", ["BRA", "ARG"], ("2019", "2021"), "M", 2, True)

    name, kwargs = client.calls[-1]
    assert name == "get_data"
    assert kwargs["country"] == ["BRA", "ARG"]
    assert kwargs["date"] == ("2019", "2021")
    assert kwargs["freq"] == "M"
    assert kwargs["parse_dates"] is True


def test_gateway_maps_network_failures_to_upstream_unavailable():
    gateway = WorldBankGateway(RecordingClient(requests.ConnectionError("no route to host")))

    with pytest.raises(UpstreamUnavailableError) as raised:
        gateway.sources()

    assert raised.value.status_code == 502
    assert isinstance(raised.value.__cause__, requests.ConnectionError)


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("Got error 120 (Invalid value): The provided parameter value is not valid"),
        ValueError("Only one of indicator, source and topic may be given."),
        IndexError("tuple index out of range"),
    ],
)
def test_gateway_maps_library_rejections_to_invalid_request(error):
    gateway = WorldBankGateway(RecordingClient(error))

    with pytest.raises(InvalidRequestError) as raised:
        gateway.indicators("NOT.A.CODE")

    assert raised.value.status_code == 400
    assert raised.value.message == str(error)


def test_gateway_maps_a_missing_frequency_or_period_to_not_found():
    gateway = WorldBankGateway(RecordingClient(TypeError("'NoneType' object is not iterable")))

    with pytest.raises(NotFoundError) as raised:
        gateway.data("NY.GDP.PCAP.CD", "BRA", "2021", "Q", None, False)

    assert raised.value.status_code == 404
    assert "no data" in raised.value.message


def test_gateway_returns_the_library_answer():
    gateway = WorldBankGateway(RecordingClient())

    assert gateway.sources() == [{"id": "ok"}]


def test_default_gateway_uses_an_uncached_client():
    gateway = WorldBankGateway()

    assert isinstance(gateway._client, UncachedClient)
