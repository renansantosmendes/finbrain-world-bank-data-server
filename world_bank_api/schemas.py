"""Response and request models. They document the API in the Swagger UI.

Records come from the World Bank API with more fields than listed here, so every
model keeps the extra fields (``extra="allow"``): documenting a field never
hides it from a client.
"""

from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Body returned with every error status.

    Attributes
    ----------
    code : str
        Machine-readable error code, for example ``invalid_request``.
    message : str
        Explanation for people.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        description=(
            "Machine-readable error code: `invalid_request` (400), `not_found` "
            "(404), `upstream_unavailable` (502) or `internal_error` (500)."
        ),
        examples=["invalid_request"],
    )
    message: str = Field(
        description="Explanation of the error, written for a person.",
        examples=["freq must be one of Y (yearly), Q (quarterly) or M (monthly)."],
    )


class HealthResponse(BaseModel):
    """Result of the liveness check.

    Attributes
    ----------
    status : str
        ``ok`` while the server accepts requests.
    """

    status: Literal["ok"] = Field(description="`ok` while the server accepts requests.")


class VersionResponse(BaseModel):
    """Versions of the server and of the wbdata library it uses.

    Attributes
    ----------
    server : str
        Version of this API.
    wbdata : str
        Version of the wbdata library that talks to the World Bank API.
    """

    server: str = Field(description="Version of this API.", examples=["0.1.0"])
    wbdata: str = Field(description="Version of the wbdata library.", examples=["1.1.0"])


class NamedReference(BaseModel):
    """An id with a human-readable value, used for linked groups.

    Attributes
    ----------
    id : str
        Code of the group, for example ``LCN``.
    value : str
        Name of the group, for example ``Latin America & Caribbean``.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Code of the group.", examples=["LCN"])
    value: Optional[str] = Field(default=None, description="Name of the group.", examples=["Latin America & Caribbean"])


class SourceRecord(BaseModel):
    """A World Bank data source, such as World Development Indicators.

    Attributes
    ----------
    id : str
        Source id, used as the ``source`` filter elsewhere.
    name : str
        Full name of the source.
    code : str
        Short code, for example ``WDI``.
    lastupdated : Optional[str]
        Date of the last update, ``YYYY-MM-DD``.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Source id; pass it as the `source` filter.", examples=["2"])
    name: str = Field(description="Full name of the source.", examples=["World Development Indicators"])
    code: Optional[str] = Field(default=None, description="Short code of the source.", examples=["WDI"])
    lastupdated: Optional[str] = Field(default=None, description="Date of the last update.", examples=["2026-10-08"])
    description: Optional[str] = Field(default=None, description="Description of the source.")
    url: Optional[str] = Field(default=None, description="Web page of the source.")


class TopicRecord(BaseModel):
    """A thematic topic, such as Environment or Education.

    Attributes
    ----------
    id : str
        Topic id, used as the ``topic`` filter of indicator search.
    value : str
        Name of the topic.
    sourceNote : Optional[str]
        Text describing the topic.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Topic id; pass it as the `topic` filter.", examples=["6"])
    value: str = Field(description="Name of the topic.", examples=["Environment"])
    sourceNote: Optional[str] = Field(default=None, description="Text describing the topic.")


class CountryRecord(BaseModel):
    """A country or a regional or income aggregate.

    Attributes
    ----------
    id : str
        ISO3 code, for example ``BRA``. Aggregates have codes too (``LCN``).
    iso2Code : Optional[str]
        ISO2 code, for example ``BR``.
    name : str
        Name of the country or aggregate.
    region : Optional[NamedReference]
        Region the country belongs to; aggregates have a region too.
    incomeLevel : Optional[NamedReference]
        Income group of the country.
    lendingType : Optional[NamedReference]
        Lending type of the country.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="ISO3 code of the country or aggregate.", examples=["BRA"])
    iso2Code: Optional[str] = Field(default=None, description="ISO2 code.", examples=["BR"])
    name: str = Field(description="Name of the country or aggregate.", examples=["Brazil"])
    region: Optional[NamedReference] = Field(default=None, description="Region of the country.")
    incomeLevel: Optional[NamedReference] = Field(default=None, description="Income group.")
    lendingType: Optional[NamedReference] = Field(default=None, description="Lending type.")
    capitalCity: Optional[str] = Field(default=None, description="Capital city.", examples=["Brasilia"])


class IncomeLevelRecord(BaseModel):
    """An income group, such as High income or Low income.

    Attributes
    ----------
    id : str
        Code of the group, used as the ``incomelevel`` filter.
    iso2code : Optional[str]
        Two-letter code of the group.
    value : str
        Name of the group.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Income level code; pass it as the `incomelevel` filter.", examples=["LIC"])
    iso2code: Optional[str] = Field(default=None, description="Two-letter code of the group.")
    value: str = Field(description="Name of the group.", examples=["Low income"])


class LendingTypeRecord(BaseModel):
    """A lending type, such as IBRD or IDA.

    Attributes
    ----------
    id : str
        Code of the lending type, used as the ``lendingtype`` filter.
    iso2code : Optional[str]
        Two-letter code of the lending type.
    value : str
        Name of the lending type.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Lending type code; pass it as the `lendingtype` filter.", examples=["IDX"])
    iso2code: Optional[str] = Field(default=None, description="Two-letter code.")
    value: str = Field(description="Name of the lending type; IDX is IDA.", examples=["IDA"])


class IndicatorRecord(BaseModel):
    """An indicator: a measure with a code, a name, a unit and a source.

    Attributes
    ----------
    id : str
        Indicator code, for example ``NY.GDP.PCAP.CD``.
    name : str
        Name of the indicator.
    unit : Optional[str]
        Unit of the values, when the source gives one.
    source : Optional[NamedReference]
        Source the indicator comes from.
    sourceNote : Optional[str]
        Methodology note.
    topics : Optional[list[NamedReference]]
        Topics the indicator belongs to.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Indicator code.", examples=["NY.GDP.PCAP.CD"])
    name: str = Field(description="Name of the indicator.", examples=["GDP per capita (current US$)"])
    unit: Optional[str] = Field(default=None, description="Unit of the values; empty when the source gives none.")
    source: Optional[NamedReference] = Field(default=None, description="Source of the indicator.")
    sourceNote: Optional[str] = Field(default=None, description="Methodology note of the indicator.")
    topics: Optional[list[NamedReference]] = Field(default=None, description="Topics of the indicator.")


class ObservationRecord(BaseModel):
    """One value of one indicator for one country and one period.

    Attributes
    ----------
    indicator : NamedReference
        Indicator the value belongs to.
    country : NamedReference
        Country the value belongs to (ISO2 id and name).
    countryiso3code : Optional[str]
        ISO3 code of the country.
    date : Union[str, datetime]
        Period of the value; a string such as ``2021``, or a datetime when
        ``parse_dates`` is set.
    value : Optional[float]
        The value; null when the source has no value for the period.
    decimal : Optional[int]
        Number of decimal places the source reports.
    """

    model_config = ConfigDict(extra="allow")

    indicator: NamedReference = Field(description="Indicator of the value.")
    country: NamedReference = Field(description="Country of the value.")
    countryiso3code: Optional[str] = Field(default=None, description="ISO3 code of the country.", examples=["BRA"])
    date: Union[str, datetime] = Field(description="Period of the value.", examples=["2021"])
    value: Optional[float] = Field(default=None, description="The value; null when missing.", examples=[7972.54])
    unit: Optional[str] = Field(default=None, description="Unit of the value.")
    obs_status: Optional[str] = Field(default=None, description="Observation status flag from the source.")
    decimal: Optional[int] = Field(default=None, description="Decimal places reported by the source.")


class SeriesPoint(BaseModel):
    """One point of an indicator series for one country.

    Attributes
    ----------
    date : str
        Period of the point.
    value : Optional[float]
        Value at that period; null when missing.
    """

    date: str = Field(description="Period of the point.", examples=["2021"])
    value: Optional[float] = Field(default=None, description="Value at the period; null when missing.", examples=[209550294])


class TableRow(BaseModel):
    """One row of a table that merges several indicators.

    Every row has a ``date`` (the period). When several countries are requested
    it also has a ``country`` (ISO3 code). Each indicator adds one column named
    after the ``indicators`` map, and a missing value is null.

    Attributes
    ----------
    date : Union[str, datetime]
        Period of the row.
    country : Optional[str]
        ISO3 code of the country; present when several countries are requested.
    """

    model_config = ConfigDict(extra="allow")

    date: Union[str, datetime] = Field(description="Period of the row.", examples=["2021"])
    country: Optional[str] = Field(
        default=None,
        description="ISO3 code of the country; null when only one country is requested.",
        examples=["BRA"],
    )


class DataframeRequest(BaseModel):
    """Body of ``POST /data/table``: several indicators merged into one table.

    Attributes
    ----------
    indicators : dict[str, str]
        Indicator codes mapped to the column names to give them.
    country : str
        ISO3 code(s), comma-separated, or ``all``.
    date_start : Optional[str]
        First period.
    date_end : Optional[str]
        Last period; omit it for one period.
    freq : str
        ``Y``, ``Q`` or ``M``.
    source : Optional[int]
        Source id; default 2 (World Development Indicators).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "indicators": {"NY.GDP.PCAP.CD": "gdp_per_capita", "SP.POP.TOTL": "population"},
                    "country": "BRA",
                    "date_start": "2019",
                    "date_end": "2021",
                    "freq": "Y",
                }
            ]
        }
    )

    indicators: dict[str, str] = Field(
        description=(
            "Indicator codes mapped to the column names. At least one entry is "
            "required. Example: `{\"NY.GDP.PCAP.CD\": \"gdp_per_capita\"}`."
        ),
    )
    country: str = Field(default="all", description="ISO3 code(s), comma-separated, or `all`.", examples=["BRA,ARG"])
    date_start: Optional[str] = Field(default=None, description="First period, such as `2019`.", examples=["2019"])
    date_end: Optional[str] = Field(default=None, description="Last period, such as `2021`; needs `date_start`.", examples=["2021"])
    freq: str = Field(default="Y", pattern="^[YQMyqm]$", description="`Y` (yearly), `Q` (quarterly) or `M` (monthly).")
    source: Optional[int] = Field(default=None, description="Source id; default 2 (World Development Indicators).", examples=[2])
