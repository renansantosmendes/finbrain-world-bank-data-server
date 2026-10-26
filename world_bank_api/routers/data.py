"""Data routes: observations, one series and a table of several indicators."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Path, Query

from world_bank_api.dependencies import get_service
from world_bank_api.routers.common import error_responses
from world_bank_api.schemas import DataframeRequest, ObservationRecord, SeriesPoint, TableRow
from world_bank_api.service import WorldBankService

router = APIRouter(tags=["Data"])

PERIOD_DESCRIPTION = (
    "Period in the format of the frequency: a year (`2021`), a quarter "
    "(`2021Q1`) or a month (`2021M01` or `2021-01`)."
)


@router.get(
    "/data/{code}",
    response_model=list[ObservationRecord],
    summary="Get the observations of one indicator",
    description="""\
Returns the **observations** of one indicator: one record per country and period,
with the value, the period and the country. Use this endpoint when you need
several countries at once, or when you want the full record of each value.

Arguments:

- `country`: `all` (default, every country and aggregate), one ISO3 code, or
  several separated by commas. Example: `BRA,ARG`.
- `date_start` and `date_end`: a period range. Give only `date_start` to read one
  period. `date_end` on its own is rejected.
- `freq`: `Y` (yearly, default), `Q` (quarterly) or `M` (monthly). An indicator
  returns only the frequencies it publishes; most indicators are yearly.
- `source`: a source id (see `/sources`). The default is `2` (World Development
  Indicators).
- `parse_dates`: when `true`, the `date` field is parsed as a datetime.

A missing value is returned with `value: null`. Responds `404` when the
combination of code, country and period has no observation at all.
""",
    responses=error_responses(400, 404, 502),
)
def get_observations(
    code: str = Path(
        description="Indicator code, such as `NY.GDP.PCAP.CD`.",
        examples=["NY.GDP.PCAP.CD"],
    ),
    country: Optional[str] = Query(
        default="all",
        description="`all`, one ISO3 code, or several separated by commas (`BRA,ARG`).",
        examples=["BRA"],
    ),
    date_start: Optional[str] = Query(
        default=None,
        description=f"First period. {PERIOD_DESCRIPTION}",
        examples=["2019"],
    ),
    date_end: Optional[str] = Query(
        default=None,
        description=f"Last period, inclusive. Needs `date_start`. {PERIOD_DESCRIPTION}",
        examples=["2021"],
    ),
    freq: str = Query(
        default="Y",
        pattern="^[YQMyqm]$",
        description="Frequency: `Y` (yearly), `Q` (quarterly) or `M` (monthly).",
        examples=["Y"],
    ),
    source: Optional[int] = Query(
        default=None,
        description="Source id; the default is 2 (World Development Indicators).",
        examples=[2],
    ),
    parse_dates: bool = Query(
        default=False,
        description="Return the `date` field as a datetime instead of text.",
    ),
    service: WorldBankService = Depends(get_service),
) -> list[dict[str, Any]]:
    """Return the observations of one indicator.

    Parameters
    ----------
    code : str
        Indicator code.
    country : Optional[str]
        ISO3 code(s), or `all`.
    date_start : Optional[str]
        First period.
    date_end : Optional[str]
        Last period.
    freq : str
        Frequency.
    source : Optional[int]
        Source id.
    parse_dates : bool
        Parse the period as a datetime.
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    list[dict[str, Any]]
        Observation records.
    """
    return service.get_observations(
        code=code,
        country=country,
        date_start=date_start,
        date_end=date_end,
        freq=freq,
        source=source,
        parse_dates=parse_dates,
    )


@router.get(
    "/series/{code}",
    response_model=list[SeriesPoint],
    summary="Get one indicator as a time series",
    description="""\
Returns one indicator for **one** country as a time series: a list of
`{date, value}` points in period order. This is the simplest shape to plot.

Arguments are the same as `/data/{code}`, except that `country` takes a
single ISO3 code (`BRA`). For several countries, use `/data/{code}` or the table
endpoint `POST /data/table`.

Responds `404` when the country has no observation for the indicator and period.
""",
    responses=error_responses(400, 404, 502),
)
def get_series(
    code: str = Path(
        description="Indicator code, such as `SP.POP.TOTL`.",
        examples=["SP.POP.TOTL"],
    ),
    country: str = Query(
        default="all",
        description="One ISO3 code, such as `BRA`, or `all` (the series of every country).",
        examples=["BRA"],
    ),
    date_start: Optional[str] = Query(
        default=None,
        description=f"First period. {PERIOD_DESCRIPTION}",
        examples=["2020"],
    ),
    date_end: Optional[str] = Query(
        default=None,
        description=f"Last period, inclusive. Needs `date_start`. {PERIOD_DESCRIPTION}",
        examples=["2022"],
    ),
    freq: str = Query(
        default="Y",
        pattern="^[YQMyqm]$",
        description="Frequency: `Y` (yearly), `Q` (quarterly) or `M` (monthly).",
        examples=["Y"],
    ),
    source: Optional[int] = Query(
        default=None,
        description="Source id; the default is 2 (World Development Indicators).",
        examples=[2],
    ),
    service: WorldBankService = Depends(get_service),
) -> list[dict[str, Any]]:
    """Return one indicator as a list of date/value points.

    Parameters
    ----------
    code : str
        Indicator code.
    country : str
        One ISO3 code, or `all`.
    date_start : Optional[str]
        First period.
    date_end : Optional[str]
        Last period.
    freq : str
        Frequency.
    source : Optional[int]
        Source id.
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    list[dict[str, Any]]
        Points with `date` and `value`.
    """
    return service.get_series(
        code=code,
        country=country,
        date_start=date_start,
        date_end=date_end,
        freq=freq,
        source=source,
    )


@router.post(
    "/data/table",
    response_model=list[TableRow],
    summary="Merge several indicators into one table",
    description="""\
Downloads several indicators and merges them into **one table**: one row per
period (and per country, when several countries are requested), with one column
per indicator.

The body gives:

- `indicators`: a map from indicator code to the column name you want, for
  example `{"NY.GDP.PCAP.CD": "gdp_per_capita", "SP.POP.TOTL": "population"}`.
  At least one entry is required.
- `country`: `all` (default), one ISO3 code, or several separated by commas.
- `date_start` and `date_end`: the period range, as in `/data/{code}`.
- `freq`: `Y` (default), `Q` or `M`.
- `source`: a source id; the default is `2`.

Each row has a `date` field with the period, a `country` field with the ISO3 code
(`null` when only one country is requested), and one field per column name. A
missing value is `null`.

Responds `400` when the body is invalid and `404` when the table is empty.
""",
    responses=error_responses(400, 404, 502),
)
def get_table(
    body: DataframeRequest,
    service: WorldBankService = Depends(get_service),
) -> list[dict[str, Any]]:
    """Return several indicators merged into one table.

    Parameters
    ----------
    body : DataframeRequest
        Indicators, countries, period range, frequency and source.
    service : WorldBankService
        Service injected by FastAPI.

    Returns
    -------
    list[dict[str, Any]]
        Table rows.
    """
    return service.get_table(
        indicators=body.indicators,
        country=body.country,
        date_start=body.date_start,
        date_end=body.date_end,
        freq=body.freq,
        source=body.source,
    )
