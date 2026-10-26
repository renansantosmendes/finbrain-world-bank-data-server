"""Static settings of the API: title, version, documentation and tags.

The server has no runtime configuration: it reads no environment variables and
keeps no state, so it can run as a serverless function.
"""

from wbdata import version as wbdata_version

SERVER_VERSION = "0.1.0"
WBDATA_VERSION = wbdata_version.__version__

TITLE = "FinBrain World Bank Data Server"

DESCRIPTION = """\
Stateless HTTP API over the **World Bank Open Data** catalogue and indicator
series, built on the [wbdata](https://github.com/OliverSherouse/wbdata) library.

Every request is answered by the World Bank API at the time of the call. The
server keeps **no cache** and writes nothing to disk, so it runs safely on
serverless platforms such as Vercel.

## What you can read

- **Catalogue**: data sources, thematic topics, countries and aggregates,
  income levels and lending types.
- **Indicators**: search by name, source or topic, and read one indicator by code.
- **Data**: observations as records, as one indicator series, or as a table
  that merges several indicators.

## Conventions

- **Country codes** are ISO3 codes such as `BRA` (Brazil). Several countries
  are comma-separated (`BRA,ARG`). `all` means every country and aggregate.
- **Periods** are years (`2021`), quarters (`2021Q1`) or months (`2021M01` or
  `2021-01`). A range uses two values, `date_start` and `date_end`.
- **Frequency** (`freq`) is `Y` (yearly), `Q` (quarterly) or `M` (monthly). An
  indicator only returns the frequencies it publishes; most World Development
  Indicators are yearly.
- **Missing values** are returned as `null`.
- **Errors** share one shape: `{"code": "...", "message": "..."}`.
  `400` means the request is invalid, `404` means nothing matched, and `502`
  means the World Bank API could not be reached.

## Authentication

None. The data is public and the API is read-only.

## Data attribution

The data belongs to the World Bank and is shared under its open-data terms. Keep
the source (`source` fields in the responses) when you publish it.
"""

TAGS = [
    {
        "name": "System",
        "description": "Health check and version information.",
    },
    {
        "name": "Catalogue",
        "description": (
            "Reference data: data sources, thematic topics, countries and "
            "aggregates, income levels and lending types. Use these ids and "
            "codes as filters in the other endpoints."
        ),
    },
    {
        "name": "Indicators",
        "description": (
            "Find indicators by name, source or topic, and read one indicator's "
            "metadata. Indicator codes such as `NY.GDP.PCAP.CD` feed the Data "
            "endpoints."
        ),
    },
    {
        "name": "Data",
        "description": (
            "Observations of one or several indicators for one or several "
            "countries and periods."
        ),
    },
]
