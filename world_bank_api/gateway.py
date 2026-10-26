"""Adapter over the wbdata library: the only module that calls the World Bank API.

wbdata keeps an on-disk cache of responses. Serverless hosts such as Vercel
only allow writes under the temporary directory, so this module never uses
that cache: ``UncachedClient`` replaces it with ``NoCache``, which stores
nothing, and every call goes to the World Bank API.

Importing ``wbdata`` also builds a default client that opens its cache file; the
package ``world_bank_api`` moves that cache location to the temporary directory
before this module is imported. The default client is never used for requests.
"""

from collections.abc import Iterator, MutableMapping
from typing import Any, Callable, Optional, Union

import requests
import wbdata
from wbdata import client as wbdata_client
from wbdata import fetcher as wbdata_fetcher

from world_bank_api.errors import InvalidRequestError, NotFoundError, UpstreamUnavailableError

CountrySelector = Union[str, list[str], None]

NO_DATA_MESSAGE = (
    "The World Bank API returned no data for this request. Check the indicator, "
    "the country, the period and the frequency: an indicator only has the "
    "frequencies it publishes."
)


class NoCache(MutableMapping):
    """A response cache that never keeps anything.

    Reads always miss and writes are discarded, so no file is created and no
    response survives the request that fetched it.

    Example
    -------
    >>> cache = NoCache()
    >>> cache["key"] = "value"
    >>> "key" in cache
    False
    """

    def __getitem__(self, key: Any) -> Any:
        raise KeyError(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        return None

    def __delitem__(self, key: Any) -> None:
        raise KeyError(key)

    def __iter__(self) -> Iterator[Any]:
        return iter(())

    def __len__(self) -> int:
        return 0


class UncachedClient(wbdata.Client):
    """A wbdata client that fetches every response from the World Bank API.

    It has the same methods as ``wbdata.Client``; only the response cache is
    replaced by ``NoCache``. The default ``wbdata.Client`` opens a cache file in
    its constructor, which this class avoids.

    Example
    -------
    >>> client = UncachedClient()
    >>> isinstance(client.fetcher.cache, NoCache)
    True
    """

    def __post_init__(self) -> None:
        session = self.session
        if session is None:
            self.fetcher = wbdata_fetcher.Fetcher(cache=NoCache())
        else:
            self.fetcher = wbdata_fetcher.Fetcher(cache=NoCache(), session=session)
        self.has_pandas = wbdata_client.pd is not None


class WorldBankGateway:
    """Calls the World Bank API through wbdata and translates its failures.

    Each method maps one call of ``wbdata.Client`` and forwards its arguments
    unchanged. Library and network errors become the application errors in
    ``world_bank_api.errors``.

    Parameters
    ----------
    client : Optional[wbdata.Client]
        Client to call. Defaults to an ``UncachedClient``.

    Example
    -------
    >>> gateway = WorldBankGateway()
    >>> sources = gateway.sources()  # doctest: +SKIP
    """

    def __init__(self, client: Optional[wbdata.Client] = None) -> None:
        self._client = client if client is not None else UncachedClient()

    def sources(self, source_id: Optional[str] = None) -> Any:
        """Fetch data sources, all of them or one by id.

        Parameters
        ----------
        source_id : Optional[str]
            Source id, or None for every source.

        Returns
        -------
        Any
            The wbdata result: a list of source records.
        """
        return self._call(self._client.get_sources, source_id=source_id, skip_cache=True)

    def topics(self, topic_id: Optional[str] = None) -> Any:
        """Fetch thematic topics, all of them or one by id.

        Parameters
        ----------
        topic_id : Optional[str]
            Topic id, or None for every topic.

        Returns
        -------
        Any
            The wbdata result: a list of topic records.
        """
        return self._call(self._client.get_topics, topic_id=topic_id, skip_cache=True)

    def countries(
        self,
        country_id: CountrySelector = None,
        query: Optional[str] = None,
        incomelevel: Optional[str] = None,
        lendingtype: Optional[str] = None,
    ) -> Any:
        """Fetch countries and aggregates, optionally filtered.

        Parameters
        ----------
        country_id : CountrySelector
            ISO3 code, a list of codes, or None.
        query : Optional[str]
            Regular expression matched against the country name.
        incomelevel : Optional[str]
            Income level id, for example ``LIC``.
        lendingtype : Optional[str]
            Lending type id, for example ``IDX``.

        Returns
        -------
        Any
            The wbdata result: a list of country records.
        """
        return self._call(
            self._client.get_countries,
            country_id=country_id,
            query=query,
            incomelevel=incomelevel,
            lendingtype=lendingtype,
            skip_cache=True,
        )

    def income_levels(self) -> Any:
        """Fetch the income level groups.

        Returns
        -------
        Any
            The wbdata result: a list of income level records.
        """
        return self._call(self._client.get_incomelevels, skip_cache=True)

    def lending_types(self) -> Any:
        """Fetch the lending type groups.

        Returns
        -------
        Any
            The wbdata result: a list of lending type records.
        """
        return self._call(self._client.get_lendingtypes, skip_cache=True)

    def indicators(
        self,
        indicator: Optional[Union[str, list[str]]] = None,
        query: Optional[str] = None,
        source: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Any:
        """Search indicators by code, name, source or topic.

        Parameters
        ----------
        indicator : Optional[Union[str, list[str]]]
            Indicator code, or a list of codes.
        query : Optional[str]
            Regular expression matched against the indicator name.
        source : Optional[str]
            Source id whose indicators are listed.
        topic : Optional[str]
            Topic id whose indicators are listed.

        Returns
        -------
        Any
            The wbdata result: a list of indicator records.
        """
        return self._call(
            self._client.get_indicators,
            indicator=indicator,
            query=query,
            source=source,
            topic=topic,
            skip_cache=True,
        )

    def data(
        self,
        indicator: str,
        country: CountrySelector,
        date: Any,
        freq: str,
        source: Optional[int],
        parse_dates: bool,
    ) -> Any:
        """Fetch observations of one indicator as records.

        Parameters
        ----------
        indicator : str
            Indicator code.
        country : CountrySelector
            ISO3 code, a list of codes, or ``all``.
        date : Any
            None, one period, or a ``(start, end)`` pair.
        freq : str
            ``Y``, ``Q`` or ``M``.
        source : Optional[int]
            Source id, or None for the default source.
        parse_dates : bool
            Whether to return periods as datetimes.

        Returns
        -------
        Any
            The wbdata result: a list of observation records.
        """
        return self._call(
            self._client.get_data,
            indicator=indicator,
            country=country,
            date=date,
            freq=freq,
            source=source,
            parse_dates=parse_dates,
            skip_cache=True,
        )

    def series(
        self,
        indicator: str,
        country: CountrySelector,
        date: Any,
        freq: str,
        source: Optional[int],
    ) -> Any:
        """Fetch one indicator as a pandas Series indexed by period.

        Parameters
        ----------
        indicator : str
            Indicator code.
        country : CountrySelector
            One ISO3 code, or ``all``.
        date : Any
            None, one period, or a ``(start, end)`` pair.
        freq : str
            ``Y``, ``Q`` or ``M``.
        source : Optional[int]
            Source id, or None for the default source.

        Returns
        -------
        Any
            A pandas Series.
        """
        return self._call(
            self._client.get_series,
            indicator=indicator,
            country=country,
            date=date,
            freq=freq,
            source=source,
            skip_cache=True,
        )

    def table(
        self,
        indicators: dict[str, str],
        country: CountrySelector,
        date: Any,
        freq: str,
        source: Optional[int],
    ) -> Any:
        """Fetch several indicators merged into one pandas DataFrame.

        Parameters
        ----------
        indicators : dict[str, str]
            Indicator codes mapped to the column names to give them.
        country : CountrySelector
            ISO3 code(s), or ``all``.
        date : Any
            None, one period, or a ``(start, end)`` pair.
        freq : str
            ``Y``, ``Q`` or ``M``.
        source : Optional[int]
            Source id, or None for the default source.

        Returns
        -------
        Any
            A pandas DataFrame.
        """
        return self._call(
            self._client.get_dataframe,
            indicators=indicators,
            country=country,
            date=date,
            freq=freq,
            source=source,
            skip_cache=True,
        )

    def _call(self, function: Callable[..., Any], **kwargs: Any) -> Any:
        """Run one wbdata call and translate its failures.

        Parameters
        ----------
        function : Callable[..., Any]
            Client method to run.
        **kwargs : Any
            Arguments of that method.

        Returns
        -------
        Any
            The value returned by the method.

        Raises
        ------
        UpstreamUnavailableError
            When the network request fails.
        NotFoundError
            When wbdata has no data to return for the request; it fails with
            a TypeError in that case.
        InvalidRequestError
            When wbdata or the API rejects the arguments.
        """
        try:
            return function(**kwargs)
        except requests.RequestException as error:
            raise UpstreamUnavailableError("The World Bank API could not be reached.") from error
        except TypeError as error:
            raise NotFoundError(NO_DATA_MESSAGE) from error
        except (ValueError, IndexError, RuntimeError) as error:
            raise InvalidRequestError(str(error)) from error
