"""Indicator routes: search indicators and read one indicator's metadata."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Path, Query

from world_bank_api.dependencies import get_service
from world_bank_api.routers.common import error_responses
from world_bank_api.schemas import IndicatorRecord
from world_bank_api.service import WorldBankService

router = APIRouter(prefix="/indicators", tags=["Indicators"])


@router.get(
    "",
    response_model=list[IndicatorRecord],
    summary="Search indicators by code, name, source or topic",
    description="""\
Searches the World Bank indicators. An indicator is a measure with a **code**
such as `NY.GDP.PCAP.CD` (GDP per capita, current US$) or `SP.POP.TOTL`
(total population).

Use one of these filters, or combine them as described:

- `indicator`: one code or several separated by commas. Returns those indicators.
- `query`: a case-insensitive regular expression matched against the name, for
  example `inflation` or `gdp per capita`.
- `source`: a source id (see `/sources`). Returns the indicators of that source.
- `topic`: a topic id (see `/topics`). Returns the indicators of that topic.

`indicator`, `source` and `topic` are alternatives: use one of them at a time.
`query` can be added to `source` or `topic` to narrow the results by name.

Each record gives the code, the name, the unit, the source and the topics.
Responds `404` when nothing matches.
""",
    responses=error_responses(400, 404, 502),
)
def search_indicators(
    indicator: Optional[str] = Query(
        default=None,
        description="Indicator code(s), comma-separated, such as `NY.GDP.PCAP.CD`.",
        examples=["NY.GDP.PCAP.CD,SP.POP.TOTL"],
    ),
    query: Optional[str] = Query(
        default=None,
        description="Regular expression matched against the indicator name (case-insensitive).",
        examples=["inflation"],
    ),
    source: Optional[str] = Query(
        default=None,
        description="Source id whose indicators are listed, such as `2`.",
        examples=["2"],
    ),
    topic: Optional[str] = Query(
        default=None,
        description="Topic id whose indicators are listed, such as `6`.",
        examples=["6"],
    ),
    service: WorldBankService = Depends(get_service),
) -> list[dict[str, Any]]:
    """Search indicators with the given filters.

    Parameters
    ----------
    indicator : Optional[str]
        Indicator code(s).
    query : Optional[str]
        Name pattern.
    source : Optional[str]
        Source id.
    topic : Optional[str]
        Topic id.
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    list[dict[str, Any]]
        Indicator records.
    """
    return service.search_indicators(
        indicator=indicator,
        query=query,
        source=source,
        topic=topic,
    )


@router.get(
    "/{code}",
    response_model=IndicatorRecord,
    summary="Get one indicator by code",
    description="""\
Returns the metadata of one indicator: its name, its unit, the source it comes
from, the topics it belongs to and the methodology note.

The values themselves come from the Data endpoints, such as
`/data/{code}` for observations or `/series/{code}` for a series.

Responds `404` when the code is unknown.
""",
    responses=error_responses(404, 502),
)
def get_indicator(
    code: str = Path(
        description="Indicator code, such as `NY.GDP.PCAP.CD`.",
        examples=["NY.GDP.PCAP.CD"],
    ),
    service: WorldBankService = Depends(get_service),
) -> dict[str, Any]:
    """Return one indicator's metadata.

    Parameters
    ----------
    code : str
        Indicator code, such as `NY.GDP.PCAP.CD`.
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    dict[str, Any]
        The indicator record.
    """
    return service.get_indicator(code)
