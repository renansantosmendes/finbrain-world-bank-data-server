"""FinBrain World Bank Data Server: a stateless HTTP API over wbdata.

This package runs before any of its submodules, so it is where the wbdata cache
location is moved to the temporary directory. Importing ``wbdata`` builds a
default client that opens its cache file; the temporary directory is the only
location that is writable on serverless hosts, and the API never uses that
cache.
"""

import os
import tempfile

os.environ.setdefault(
    "WBDATA_CACHE_PATH",
    os.path.join(tempfile.gettempdir(), "wbdata-import", "cache"),
)
