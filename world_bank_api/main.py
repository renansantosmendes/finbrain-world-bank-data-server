"""Application factory: builds the FastAPI app, its routers and its error handling.

``app`` is the instance served by Uvicorn locally and by Vercel
(``api/index.py``).
"""

from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from world_bank_api.config import DESCRIPTION, SERVER_VERSION, TAGS, TITLE
from world_bank_api.errors import InvalidRequestError, WorldBankError
from world_bank_api.routers import catalogue, data, indicators, system


def error_body(code: str, message: str) -> dict[str, str]:
    """Build the JSON body of an error response.

    Parameters
    ----------
    code : str
        Machine-readable error code.
    message : str
        Explanation for people.

    Returns
    -------
    dict[str, str]
        ``{"code": ..., "message": ...}``.

    Example
    -------
    >>> error_body("not_found", "No country matches the request.")["code"]
    'not_found'
    """
    return {"code": code, "message": message}


def validation_message(error: dict[str, Any]) -> str:
    """Describe one FastAPI validation error in one readable sentence.

    Parameters
    ----------
    error : dict[str, Any]
        One entry of ``RequestValidationError.errors()``.

    Returns
    -------
    str
        The parameter name and what is wrong with it.

    Example
    -------
    >>> validation_message({"loc": ("query", "freq"), "msg": "String should match pattern"})
    'freq: String should match pattern'
    """
    location = [str(part) for part in error.get("loc", ()) if part not in ("query", "path", "body")]
    name = ".".join(location) or "request"
    return f"{name}: {error.get('msg', 'invalid value')}"


def create_app() -> FastAPI:
    """Build the application with its routers and error handlers.

    Returns
    -------
    FastAPI
        The configured application.

    Example
    -------
    >>> application = create_app()
    >>> application.title
    'FinBrain World Bank Data Server'
    """
    application = FastAPI(
        title=TITLE,
        version=SERVER_VERSION,
        description=DESCRIPTION,
        openapi_tags=TAGS,
    )
    application.include_router(system.router)
    application.include_router(catalogue.router)
    application.include_router(indicators.router)
    application.include_router(data.router)

    @application.exception_handler(WorldBankError)
    async def handle_world_bank_error(request: Request, error: WorldBankError) -> JSONResponse:
        """Answer a service or gateway error with its status and body.

        Parameters
        ----------
        request : Request
            Request that failed.
        error : WorldBankError
            The error raised by the service or the gateway.

        Returns
        -------
        JSONResponse
            Error status with the ``{"code", "message"}`` body.
        """
        return JSONResponse(
            status_code=error.status_code,
            content=error_body(error.code, error.message),
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        """Answer an invalid parameter or body with the shared error shape.

        Parameters
        ----------
        request : Request
            Request that failed validation.
        error : RequestValidationError
            Validation errors of the parameters and the body.

        Returns
        -------
        JSONResponse
            HTTP 400 with the first problem described in ``message``.
        """
        first = error.errors()[0] if error.errors() else {}
        failure = InvalidRequestError(validation_message(first))
        return JSONResponse(
            status_code=failure.status_code,
            content=error_body(failure.code, failure.message),
        )

    application.openapi = build_openapi(application)
    return application


def build_openapi(application: FastAPI) -> Callable[[], dict[str, Any]]:
    """Make the application's OpenAPI document, without FastAPI's default 422 responses.

    Validation errors are answered with HTTP 400 and the shared error body, so
    the documented 422 response and its schema are removed.

    Parameters
    ----------
    application : FastAPI
        Application whose document is built.

    Returns
    -------
    Callable[[], dict[str, Any]]
        Function that returns the cached OpenAPI document.

    Example
    -------
    >>> build_openapi(FastAPI())()["openapi"].startswith("3.")
    True
    """

    def openapi_schema() -> dict[str, Any]:
        if application.openapi_schema is not None:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
            tags=TAGS,
        )
        for methods in schema.get("paths", {}).values():
            for operation in methods.values():
                operation.get("responses", {}).pop("422", None)
        components = schema.get("components", {}).get("schemas", {})
        components.pop("HTTPValidationError", None)
        components.pop("ValidationError", None)
        application.openapi_schema = schema
        return schema

    return openapi_schema


app = create_app()
