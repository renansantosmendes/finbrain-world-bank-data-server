"""System routes: liveness check and version information."""

from fastapi import APIRouter

from world_bank_api.config import SERVER_VERSION, WBDATA_VERSION
from world_bank_api.schemas import HealthResponse, VersionResponse

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check that the server is running",
    description="""\
Liveness check. Answers `200` with `{"status": "ok"}` as long as the server
process accepts requests.

**It does not call the World Bank API**, so a `200` here says nothing about the
upstream service. Use `/sources` to check the upstream connection.

Monitoring systems and serverless platforms can call this route often: it does
no network work and no computation.
""",
    responses={200: {"description": "The server accepts requests."}},
)
def health() -> HealthResponse:
    """Report that the server is running.

    Returns
    -------
    HealthResponse
        Status ``ok``.
    """
    return HealthResponse(status="ok")


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Get the server and wbdata versions",
    description="""\
Returns the version of this API and the version of the `wbdata` library it uses
to call the World Bank API.

Include the `wbdata` version when you report a bug: the World Bank API's
responses and the library's parsing rules change between releases.
""",
    responses={200: {"description": "Both versions."}},
)
def version() -> VersionResponse:
    """Report the versions in use.

    Returns
    -------
    VersionResponse
        Server and wbdata versions.
    """
    return VersionResponse(server=SERVER_VERSION, wbdata=WBDATA_VERSION)
