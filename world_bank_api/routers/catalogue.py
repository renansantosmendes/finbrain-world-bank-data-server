"""Catalogue routes: data sources, topics, countries, income levels and lending types."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Path, Query

from world_bank_api.dependencies import get_service
from world_bank_api.routers.common import error_responses
from world_bank_api.schemas import (
    CountryRecord,
    IncomeLevelRecord,
    LendingTypeRecord,
    SourceRecord,
    TopicRecord,
)
from world_bank_api.service import WorldBankService

router = APIRouter(tags=["Catalogue"])


@router.get(
    "/sources",
    response_model=list[SourceRecord],
    summary="List the data sources",
    description="""\
Lists every data source the World Bank publishes, such as World Development
Indicators (`WDI`, id `2`) or Doing Business (id `1`).

Each source has an **id**. Pass that id as the `source` argument of the Indicators
and Data endpoints to read from a specific source. The default source, when no
`source` is given, is `2` (World Development Indicators).

Use `/sources/{source_id}` to read one source.
""",
    responses=error_responses(502),
)
def list_sources(
    service: WorldBankService = Depends(get_service),
) -> list[dict[str, Any]]:
    """List every data source.

    Parameters
    ----------
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    list[dict[str, Any]]
        Source records.
    """
    return service.list_sources()


@router.get(
    "/sources/{source_id}",
    response_model=SourceRecord,
    summary="Get one data source by id",
    description="""\
Returns one data source by its id, for example `2` for World Development
Indicators.

Responds `404` when no source has that id.
""",
    responses=error_responses(404, 502),
)
def get_source(
    source_id: str = Path(
        description="Source id, such as `2` for World Development Indicators.",
        examples=["2"],
    ),
    service: WorldBankService = Depends(get_service),
) -> dict[str, Any]:
    """Return one data source.

    Parameters
    ----------
    source_id : str
        Source id, such as `2`.
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    dict[str, Any]
        The source record.
    """
    return service.get_source(source_id)


@router.get(
    "/topics",
    response_model=list[TopicRecord],
    summary="List the thematic topics",
    description="""\
Lists the thematic topics the World Bank groups its indicators under, such as
`Environment` (id `6`), `Education` or `Energy & Mining`.

Each topic has an **id**. Pass it as the `topic` argument of
`/indicators` to list the indicators of that topic.
""",
    responses=error_responses(502),
)
def list_topics(
    service: WorldBankService = Depends(get_service),
) -> list[dict[str, Any]]:
    """List every thematic topic.

    Parameters
    ----------
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    list[dict[str, Any]]
        Topic records.
    """
    return service.list_topics()


@router.get(
    "/topics/{topic_id}",
    response_model=TopicRecord,
    summary="Get one thematic topic by id",
    description="""\
Returns one thematic topic by its id, for example `6` for `Environment`.

Responds `404` when no topic has that id.
""",
    responses=error_responses(404, 502),
)
def get_topic(
    topic_id: str = Path(
        description="Topic id, such as `6` for Environment.",
        examples=["6"],
    ),
    service: WorldBankService = Depends(get_service),
) -> dict[str, Any]:
    """Return one thematic topic.

    Parameters
    ----------
    topic_id : str
        Topic id, such as `6`.
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    dict[str, Any]
        The topic record.
    """
    return service.get_topic(topic_id)


@router.get(
    "/countries",
    response_model=list[CountryRecord],
    summary="List countries and aggregates, with filters",
    description="""\
Lists the countries and the regional or income aggregates (such as
`Latin America & Caribbean`, id `LCN`) that the World Bank publishes data for.

Every filter is optional. Filters combine as follows:

- `country_id`: one ISO3 code (`BRA`) or several separated by commas (`BRA,ARG`).
- `query`: a case-insensitive regular expression matched against the name, for
  example `^Bra` for names that start with `Bra`.
- `incomelevel`: an income group id, such as `LIC` (low income) or `HIC` (high income).
- `lendingtype`: a lending type id, such as `IDX` (IDA) or `IBD` (IBRD).

`country_id` cannot be combined with `query`, `incomelevel` or `lendingtype`:
choose one of the two styles of request. Responds `404` when nothing matches.
""",
    responses=error_responses(400, 404, 502),
)
def list_countries(
    country_id: Optional[str] = Query(
        default=None,
        description="ISO3 code(s), comma-separated, such as `BRA` or `BRA,ARG`.",
        examples=["BRA"],
    ),
    query: Optional[str] = Query(
        default=None,
        description="Regular expression matched against the name (case-insensitive).",
        examples=["^Bra"],
    ),
    incomelevel: Optional[str] = Query(
        default=None,
        description="Income level id, such as `LIC`, `LMC`, `UMC` or `HIC`.",
        examples=["LIC"],
    ),
    lendingtype: Optional[str] = Query(
        default=None,
        description="Lending type id, such as `IDX` (IDA) or `IBD` (IBRD).",
        examples=["IDX"],
    ),
    service: WorldBankService = Depends(get_service),
) -> list[dict[str, Any]]:
    """List countries and aggregates, with optional filters.

    Parameters
    ----------
    country_id : Optional[str]
        ISO3 code(s).
    query : Optional[str]
        Name pattern.
    incomelevel : Optional[str]
        Income level id.
    lendingtype : Optional[str]
        Lending type id.
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    list[dict[str, Any]]
        Country and aggregate records.
    """
    return service.list_countries(
        country_id=country_id,
        query=query,
        incomelevel=incomelevel,
        lendingtype=lendingtype,
    )


@router.get(
    "/countries/{country_id}",
    response_model=CountryRecord,
    summary="Get one country or aggregate by ISO3 code",
    description="""\
Returns one country or aggregate by its ISO3 code, for example `BRA` for Brazil
or `LCN` for Latin America & Caribbean.

The record gives the ISO2 code, the region, the income group, the lending type and
the capital city. Responds `404` when the code is unknown.
""",
    responses=error_responses(404, 502),
)
def get_country(
    country_id: str = Path(
        description="ISO3 code of the country or aggregate, such as `BRA` or `LCN`.",
        examples=["BRA"],
    ),
    service: WorldBankService = Depends(get_service),
) -> dict[str, Any]:
    """Return one country or aggregate.

    Parameters
    ----------
    country_id : str
        ISO3 code, such as `BRA`.
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    dict[str, Any]
        The country record.
    """
    return service.get_country(country_id)


@router.get(
    "/income-levels",
    response_model=list[IncomeLevelRecord],
    summary="List the income groups",
    description="""\
Lists the World Bank income groups: `HIC` (high income), `UMC` (upper middle
income), `LMC` (lower middle income) and `LIC` (low income), plus aggregates
such as `LMY` (low & middle income).

Pass one of these ids as the `incomelevel` filter of `/countries`.
""",
    responses=error_responses(404, 502),
)
def list_income_levels(
    service: WorldBankService = Depends(get_service),
) -> list[dict[str, Any]]:
    """List the income groups.

    Parameters
    ----------
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    list[dict[str, Any]]
        Income group records.
    """
    return service.list_income_levels()


@router.get(
    "/lending-types",
    response_model=list[LendingTypeRecord],
    summary="List the lending types",
    description="""\
Lists the World Bank lending types: `IBD` (IBRD, loans at market-based rates),
`IDX` (IDA, concessional loans for the poorest countries), `IDB` (blend of both)
and `LNX` (not classified).

Pass one of these ids as the `lendingtype` filter of `/countries`.
""",
    responses=error_responses(404, 502),
)
def list_lending_types(
    service: WorldBankService = Depends(get_service),
) -> list[dict[str, Any]]:
    """List the lending types.

    Parameters
    ----------
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    list[dict[str, Any]]
        Lending type records.
    """
    return service.list_lending_types()
