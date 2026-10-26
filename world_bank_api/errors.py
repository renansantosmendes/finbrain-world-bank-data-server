"""Application errors and their HTTP mapping.

Every error the API returns has the same JSON shape, ``{"code", "message"}``,
so clients can branch on ``code`` and show ``message`` to people.
"""


class WorldBankError(Exception):
    """Base class of the errors the API reports to its clients.

    Attributes
    ----------
    status_code : int
        HTTP status returned with the error.
    code : str
        Machine-readable error code.
    message : str
        Human-readable explanation.

    Example
    -------
    >>> error = WorldBankError("Something went wrong.")
    >>> (error.status_code, error.code)
    (500, 'internal_error')
    """

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidRequestError(WorldBankError):
    """The request has a parameter the World Bank API or the rules do not accept.

    Attributes
    ----------
    status_code : int
        Always 400.
    code : str
        ``invalid_request``.

    Example
    -------
    >>> InvalidRequestError("freq must be Y, Q or M.").status_code
    400
    """

    status_code = 400
    code = "invalid_request"


class NotFoundError(WorldBankError):
    """The World Bank API answered, but there is nothing for the request.

    Attributes
    ----------
    status_code : int
        Always 404.
    code : str
        ``not_found``.

    Example
    -------
    >>> NotFoundError("No country with this code.").code
    'not_found'
    """

    status_code = 404
    code = "not_found"


class UpstreamUnavailableError(WorldBankError):
    """The World Bank API could not be reached or answered with an error.

    Attributes
    ----------
    status_code : int
        Always 502.
    code : str
        ``upstream_unavailable``.

    Example
    -------
    >>> UpstreamUnavailableError("The World Bank API could not be reached.").status_code
    502
    """

    status_code = 502
    code = "upstream_unavailable"
