"""Business rules of the API: validation, normalization and not-found handling.

The service knows what the endpoints mean but nothing about HTTP or wbdata. It
asks the gateway for data, checks the arguments, and returns plain Python
records that the routers send back unchanged.
"""

import math
from typing import Any, Callable, Optional, Union

from world_bank_api.errors import InvalidRequestError, NotFoundError
from world_bank_api.gateway import CountrySelector, WorldBankGateway

FREQUENCIES = ("Y", "Q", "M")
ALL_COUNTRIES = "all"


def parse_country_codes(raw: Optional[str]) -> CountrySelector:
    """Turn a country parameter into the form wbdata expects.

    Parameters
    ----------
    raw : Optional[str]
        ``all``, one ISO3 code, or several codes separated by commas.

    Returns
    -------
    CountrySelector
        ``"all"`` for an empty value or ``all``, the code for one country, or
        a list of codes for several.

    Example
    -------
    >>> parse_country_codes("BRA, ARG")
    ['BRA', 'ARG']
    """
    if not raw or raw.strip().lower() == ALL_COUNTRIES:
        return ALL_COUNTRIES
    codes = [code.strip().upper() for code in raw.split(",") if code.strip()]
    if not codes:
        return ALL_COUNTRIES
    return codes[0] if len(codes) == 1 else codes


def parse_code_list(raw: Optional[str]) -> Optional[Union[str, list[str]]]:
    """Turn an optional comma-separated parameter into one code or a list.

    Parameters
    ----------
    raw : Optional[str]
        Comma-separated values, or None.

    Returns
    -------
    Optional[Union[str, list[str]]]
        None when the parameter is empty, one value, or a list of values.

    Example
    -------
    >>> parse_code_list("NY.GDP.PCAP.CD,SP.POP.TOTL")
    ['NY.GDP.PCAP.CD', 'SP.POP.TOTL']
    """
    if raw is None or not raw.strip():
        return None
    codes = [code.strip() for code in raw.split(",") if code.strip()]
    return codes[0] if len(codes) == 1 else codes


def validate_frequency(freq: str) -> str:
    """Check that a frequency is one the API supports.

    Parameters
    ----------
    freq : str
        Frequency code.

    Returns
    -------
    str
        The same code, in upper case.

    Raises
    ------
    InvalidRequestError
        When the code is not ``Y``, ``Q`` or ``M``.

    Example
    -------
    >>> validate_frequency("m")
    'M'
    """
    normalized = freq.strip().upper()
    if normalized not in FREQUENCIES:
        raise InvalidRequestError("freq must be one of Y (yearly), Q (quarterly) or M (monthly).")
    return normalized


def period_argument(start: Optional[str], end: Optional[str]) -> Any:
    """Build the ``date`` argument of wbdata from a start and an optional end.

    Parameters
    ----------
    start : Optional[str]
        First period, or None for every period.
    end : Optional[str]
        Last period, or None for a single period. Requires ``start``.

    Returns
    -------
    Any
        None, one period, or a ``(start, end)`` pair.

    Raises
    ------
    InvalidRequestError
        When ``end`` is given without ``start``.

    Example
    -------
    >>> period_argument("2019", "2021")
    ('2019', '2021')
    """
    if end is not None and start is None:
        raise InvalidRequestError("date_end needs date_start.")
    if start is None:
        return None
    return start if end is None else (start, end)


def number_or_none(value: Any) -> Optional[float]:
    """Convert a numeric value to a float, mapping missing values to None.

    Parameters
    ----------
    value : Any
        Number, NaN, None, or any other value.

    Returns
    -------
    Optional[float]
        The value as a float, or None when it is missing.

    Example
    -------
    >>> number_or_none(float("nan")) is None
    True
    """
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def clean_value(value: Any) -> Any:
    """Make one cell of a table JSON-safe: missing numbers become None.

    Parameters
    ----------
    value : Any
        Cell value read from a DataFrame.

    Returns
    -------
    Any
        None for a missing value; numbers and text unchanged otherwise.

    Example
    -------
    >>> clean_value(float("nan")) is None
    True
    """
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if value is None:
        return None
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return clean_value(value.item())
        except (TypeError, ValueError):
            return value
    return value


def series_points(series: Any) -> list[dict[str, Any]]:
    """Turn a pandas Series indexed by period into ``date``/``value`` records.

    Parameters
    ----------
    series : Any
        pandas Series whose index is the period.

    Returns
    -------
    list[dict[str, Any]]
        One record per period, in the order of the series.

    Example
    -------
    >>> series_points({"2021": 1.5})
    [{'date': '2021', 'value': 1.5}]
    """
    return [
        {"date": str(period), "value": number_or_none(value)}
        for period, value in series.items()
    ]


def table_records(frame: Any) -> list[dict[str, Any]]:
    """Turn a pandas DataFrame into one record per row, missing values as None.

    Parameters
    ----------
    frame : Any
        pandas DataFrame, possibly with a country or date index.

    Returns
    -------
    list[dict[str, Any]]
        One dictionary per row, with the index moved into columns.

    Example
    -------
    >>> import pandas as pd
    >>> table_records(pd.DataFrame({"gdp": [1.0]}, index=["2021"]))
    [{'index': '2021', 'gdp': 1.0}]
    """
    flat = frame.reset_index()
    rows = []
    for record in flat.to_dict(orient="records"):
        rows.append({str(key): clean_value(value) for key, value in record.items()})
    return rows


def require_records(records: Any, what: str) -> Any:
    """Return the records, or raise not-found when there are none.

    Parameters
    ----------
    records : Any
        Result of a gateway call, or None.
    what : str
        What was looked for, used in the message.

    Returns
    -------
    Any
        The records, unchanged.

    Raises
    ------
    NotFoundError
        When the result is empty.

    Example
    -------
    >>> require_records([{"id": "BRA"}], "country")
    [{'id': 'BRA'}]
    """
    if records is None or len(records) == 0:
        raise NotFoundError(f"No {what} matches the request.")
    return records


def unknown_id_as_not_found(lookup: Callable[[], Any], what: str, identifier: str) -> Any:
    """Run a lookup by id or code, reporting an invalid one as not found.

    The World Bank API answers an unknown id with the same error as an invalid
    filter. For a lookup of one item, an invalid id means that nothing matches,
    so it is reported as not found.

    Parameters
    ----------
    lookup : Callable[[], Any]
        Function that performs the lookup.
    what : str
        Kind of item looked for, used in the message.
    identifier : str
        The id or code that was requested.

    Returns
    -------
    Any
        The result of the lookup.

    Raises
    ------
    NotFoundError
        When the lookup fails because the id or code is invalid.

    Example
    -------
    >>> unknown_id_as_not_found(lambda: [1], "topic", "6")
    [1]
    """
    try:
        return lookup()
    except InvalidRequestError as error:
        raise NotFoundError(f"No {what} has the id or code {identifier}.") from error


class WorldBankService:
    """Use cases of the API, one method per capability.

    Parameters
    ----------
    gateway : WorldBankGateway
        Source of the World Bank data.

    Example
    -------
    >>> service = WorldBankService(WorldBankGateway())  # doctest: +SKIP
    """

    def __init__(self, gateway: WorldBankGateway) -> None:
        self._gateway = gateway

    def list_sources(self, source_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Return the data sources, all of them or one by id.

        Parameters
        ----------
        source_id : Optional[str]
            Source id, or None for every source.

        Returns
        -------
        list[dict[str, Any]]
            Source records.

        Raises
        ------
        NotFoundError
            When the id matches no source.
        """
        return require_records(self._gateway.sources(source_id=source_id), "data source")

    def list_topics(self, topic_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Return the thematic topics, all of them or one by id.

        Parameters
        ----------
        topic_id : Optional[str]
            Topic id, or None for every topic.

        Returns
        -------
        list[dict[str, Any]]
            Topic records.

        Raises
        ------
        NotFoundError
            When the id matches no topic.
        """
        return require_records(self._gateway.topics(topic_id=topic_id), "topic")

    def list_countries(
        self,
        country_id: Optional[str] = None,
        query: Optional[str] = None,
        incomelevel: Optional[str] = None,
        lendingtype: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return countries and aggregates, filtered by the given criteria.

        Parameters
        ----------
        country_id : Optional[str]
            ISO3 code(s), comma-separated.
        query : Optional[str]
            Regular expression matched against the name.
        incomelevel : Optional[str]
            Income level id.
        lendingtype : Optional[str]
            Lending type id.

        Returns
        -------
        list[dict[str, Any]]
            Country and aggregate records.

        Raises
        ------
        NotFoundError
            When no country matches the filters.
        """
        selector = parse_country_codes(country_id) if country_id else None
        records = self._gateway.countries(
            country_id=selector,
            query=query,
            incomelevel=incomelevel,
            lendingtype=lendingtype,
        )
        return require_records(records, "country")

    def get_source(self, source_id: str) -> dict[str, Any]:
        """Return one data source by id.

        Parameters
        ----------
        source_id : str
            Source id, such as ``2``.

        Returns
        -------
        dict[str, Any]
            The source record.

        Raises
        ------
        NotFoundError
            When the id matches no source.
        """
        records = unknown_id_as_not_found(
            lambda: self.list_sources(source_id.strip()), "data source", source_id
        )
        return records[0]

    def get_topic(self, topic_id: str) -> dict[str, Any]:
        """Return one thematic topic by id.

        Parameters
        ----------
        topic_id : str
            Topic id, such as ``6``.

        Returns
        -------
        dict[str, Any]
            The topic record.

        Raises
        ------
        NotFoundError
            When the id matches no topic.
        """
        records = unknown_id_as_not_found(
            lambda: self.list_topics(topic_id.strip()), "topic", topic_id
        )
        return records[0]

    def get_country(self, country_id: str) -> dict[str, Any]:
        """Return one country or aggregate by ISO3 code.

        Parameters
        ----------
        country_id : str
            ISO3 code such as ``BRA``.

        Returns
        -------
        dict[str, Any]
            The country record.

        Raises
        ------
        NotFoundError
            When the code matches no country.
        """
        code = country_id.strip().upper()
        records = unknown_id_as_not_found(
            lambda: require_records(self._gateway.countries(country_id=code), "country"),
            "country",
            country_id,
        )
        return records[0]

    def list_income_levels(self) -> list[dict[str, Any]]:
        """Return the income level groups.

        Returns
        -------
        list[dict[str, Any]]
            Income level records.

        Raises
        ------
        NotFoundError
            When the API returns no income levels.
        """
        return require_records(self._gateway.income_levels(), "income level")

    def list_lending_types(self) -> list[dict[str, Any]]:
        """Return the lending type groups.

        Returns
        -------
        list[dict[str, Any]]
            Lending type records.

        Raises
        ------
        NotFoundError
            When the API returns no lending types.
        """
        return require_records(self._gateway.lending_types(), "lending type")

    def search_indicators(
        self,
        indicator: Optional[str] = None,
        query: Optional[str] = None,
        source: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return indicators matching the given codes, name, source or topic.

        Parameters
        ----------
        indicator : Optional[str]
            Indicator code(s), comma-separated.
        query : Optional[str]
            Regular expression matched against the name.
        source : Optional[str]
            Source id.
        topic : Optional[str]
            Topic id.

        Returns
        -------
        list[dict[str, Any]]
            Indicator records.

        Raises
        ------
        NotFoundError
            When no indicator matches.
        """
        records = self._gateway.indicators(
            indicator=parse_code_list(indicator),
            query=query,
            source=source,
            topic=topic,
        )
        return require_records(records, "indicator")

    def get_indicator(self, code: str) -> dict[str, Any]:
        """Return the metadata of one indicator.

        Parameters
        ----------
        code : str
            Indicator code such as ``NY.GDP.PCAP.CD``.

        Returns
        -------
        dict[str, Any]
            The indicator record.

        Raises
        ------
        NotFoundError
            When the code matches no indicator.
        """
        identifier = code.strip()
        records = unknown_id_as_not_found(
            lambda: require_records(self._gateway.indicators(indicator=identifier), "indicator"),
            "indicator",
            code,
        )
        return records[0]

    def get_observations(
        self,
        code: str,
        country: Optional[str],
        date_start: Optional[str],
        date_end: Optional[str],
        freq: str,
        source: Optional[int],
        parse_dates: bool,
    ) -> list[dict[str, Any]]:
        """Return observations of one indicator, one record per country and period.

        Parameters
        ----------
        code : str
            Indicator code.
        country : Optional[str]
            ISO3 code(s), or ``all``.
        date_start : Optional[str]
            First period.
        date_end : Optional[str]
            Last period.
        freq : str
            ``Y``, ``Q`` or ``M``.
        source : Optional[int]
            Source id.
        parse_dates : bool
            Whether to return periods as datetimes.

        Returns
        -------
        list[dict[str, Any]]
            Observation records.

        Raises
        ------
        InvalidRequestError
            When the frequency or the period range is invalid.
        NotFoundError
            When no observation matches.
        """
        records = self._gateway.data(
            indicator=code.strip(),
            country=parse_country_codes(country),
            date=period_argument(date_start, date_end),
            freq=validate_frequency(freq),
            source=source,
            parse_dates=parse_dates,
        )
        return require_records(records, "observation")

    def get_series(
        self,
        code: str,
        country: Optional[str],
        date_start: Optional[str],
        date_end: Optional[str],
        freq: str,
        source: Optional[int],
    ) -> list[dict[str, Any]]:
        """Return one indicator for one country as ``date``/``value`` points.

        Parameters
        ----------
        code : str
            Indicator code.
        country : Optional[str]
            One ISO3 code, or ``all``.
        date_start : Optional[str]
            First period.
        date_end : Optional[str]
            Last period.
        freq : str
            ``Y``, ``Q`` or ``M``.
        source : Optional[int]
            Source id.

        Returns
        -------
        list[dict[str, Any]]
            Points with ``date`` and ``value`` (None when missing).

        Raises
        ------
        InvalidRequestError
            When the frequency or the period range is invalid.
        NotFoundError
            When no observation matches.
        """
        series = self._gateway.series(
            indicator=code.strip(),
            country=parse_country_codes(country),
            date=period_argument(date_start, date_end),
            freq=validate_frequency(freq),
            source=source,
        )
        return require_records(series_points(series), "observation")

    def get_table(
        self,
        indicators: dict[str, str],
        country: CountrySelector,
        date_start: Optional[str],
        date_end: Optional[str],
        freq: str,
        source: Optional[int],
    ) -> list[dict[str, Any]]:
        """Return several indicators merged into one table.

        Parameters
        ----------
        indicators : dict[str, str]
            Indicator codes mapped to column names.
        country : CountrySelector
            ISO3 code(s), or ``all``.
        date_start : Optional[str]
            First period.
        date_end : Optional[str]
            Last period.
        freq : str
            ``Y``, ``Q`` or ``M``.
        source : Optional[int]
            Source id.

        Returns
        -------
        list[dict[str, Any]]
            One record per row, with the index in ``index`` and one column per indicator.

        Raises
        ------
        InvalidRequestError
            When the frequency or the period range is invalid, or no indicator is given.
        NotFoundError
            When the table is empty.
        """
        if not indicators:
            raise InvalidRequestError("At least one indicator is required.")
        frame = self._gateway.table(
            indicators=indicators,
            country=parse_country_codes(country) if isinstance(country, str) else country,
            date=period_argument(date_start, date_end),
            freq=validate_frequency(freq),
            source=source,
        )
        return require_records(table_records(frame), "observation")
