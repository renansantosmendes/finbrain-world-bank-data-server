"""Shared documentation of the error responses used by the routers."""

from typing import Any

from world_bank_api.schemas import ErrorResponse

BAD_REQUEST = {
    "model": ErrorResponse,
    "description": (
        "The request has a value the API does not accept: an unknown frequency, "
        "a range without a start, a malformed code, or an argument the World Bank "
        "API rejects."
    ),
}

NOT_FOUND = {
    "model": ErrorResponse,
    "description": "The request is valid, but no item matches it.",
}

UPSTREAM_UNAVAILABLE = {
    "model": ErrorResponse,
    "description": (
        "The World Bank API could not be reached or did not answer. Retry later; "
        "the request itself was valid."
    ),
}


def error_responses(*statuses: int) -> dict[int, dict[str, Any]]:
    """Build the ``responses`` entries of a route for the given error statuses.

    Parameters
    ----------
    *statuses : int
        Any of 400, 404 and 502.

    Returns
    -------
    dict[int, dict[str, Any]]
        Mapping from status code to its documentation.

    Raises
    ------
    ValueError
        When a status is not one of the documented error statuses.

    Example
    -------
    >>> sorted(error_responses(400, 404))
    [400, 404]
    """
    available = {400: BAD_REQUEST, 404: NOT_FOUND, 502: UPSTREAM_UNAVAILABLE}
    documented = {}
    for status in statuses:
        if status not in available:
            raise ValueError(f"Unsupported error status: {status}")
        documented[status] = available[status]
    return documented
