"""Tests of the Swagger documentation: every route is described in detail."""

import pytest
from fastapi.testclient import TestClient

from world_bank_api.config import TAGS
from world_bank_api.main import app

EXPECTED_OPERATIONS = {
    ("get", "/health"),
    ("get", "/version"),
    ("get", "/sources"),
    ("get", "/sources/{source_id}"),
    ("get", "/topics"),
    ("get", "/topics/{topic_id}"),
    ("get", "/countries"),
    ("get", "/countries/{country_id}"),
    ("get", "/income-levels"),
    ("get", "/lending-types"),
    ("get", "/indicators"),
    ("get", "/indicators/{code}"),
    ("get", "/data/{code}"),
    ("get", "/series/{code}"),
    ("post", "/data/table"),
}

ERROR_STATUSES = {"400", "404", "502"}


@pytest.fixture(scope="module")
def schema() -> dict:
    """Provide the OpenAPI document of the application.

    Returns
    -------
    dict
        The document served at ``/openapi.json``.
    """
    return TestClient(app).get("/openapi.json").json()


def operations(schema: dict):
    """Yield every (method, path, operation) of the document.

    Parameters
    ----------
    schema : dict
        OpenAPI document.

    Yields
    ------
    tuple[str, str, dict]
        Method, path and the operation object.
    """
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            yield method, path, operation


def test_every_expected_route_is_documented(schema):
    documented = {(method, path) for method, path, _ in operations(schema)}

    assert documented == EXPECTED_OPERATIONS


def test_every_operation_has_a_summary_and_a_detailed_description(schema):
    for method, path, operation in operations(schema):
        assert operation.get("summary"), f"{method} {path} has no summary"
        assert len(operation.get("description", "")) > 100, f"{method} {path} description is too short"


def test_every_operation_belongs_to_a_declared_tag(schema):
    declared = {tag["name"] for tag in TAGS}
    for method, path, operation in operations(schema):
        tags = operation.get("tags", [])
        assert tags, f"{method} {path} has no tag"
        assert set(tags) <= declared | {"Status"}, f"{method} {path} uses an undeclared tag"


def test_every_tag_has_a_description(schema):
    for tag in schema.get("tags", []):
        assert tag.get("description"), tag["name"]


@pytest.mark.parametrize("method, path", sorted(EXPECTED_OPERATIONS))
def test_every_operation_documents_its_success_response(schema, method, path):
    responses = schema["paths"][path][method]["responses"]

    assert "200" in responses


def test_no_operation_documents_fastapi_default_validation_errors(schema):
    for method, path, operation in operations(schema):
        assert "422" not in operation["responses"], f"{method} {path} documents 422"
    assert "HTTPValidationError" not in schema["components"]["schemas"]


def test_routes_that_can_fail_document_their_error_statuses(schema):
    for method, path, operation in operations(schema):
        documented = set(operation["responses"])
        if path in ("/health", "/version"):
            continue
        assert documented & ERROR_STATUSES, f"{method} {path} documents no error status"


def test_error_responses_point_to_the_shared_error_schema(schema):
    error_schema = schema["components"]["schemas"]["ErrorResponse"]

    assert set(error_schema["properties"]) == {"code", "message"}
    for method, path, operation in operations(schema):
        for status in ERROR_STATUSES & set(operation["responses"]):
            content = operation["responses"][status]["content"]["application/json"]["schema"]
            assert content == {"$ref": "#/components/schemas/ErrorResponse"}, f"{method} {path} {status}"


def test_parameters_have_descriptions(schema):
    for method, path, operation in operations(schema):
        for parameter in operation.get("parameters", []):
            assert parameter.get("description"), f"{method} {path} parameter {parameter['name']}"


def test_request_body_is_documented_with_an_example(schema):
    body_schema = schema["components"]["schemas"]["DataframeRequest"]

    assert body_schema.get("examples")
    assert body_schema["properties"]["indicators"]["description"]


def test_swagger_ui_is_served(schema):
    response = TestClient(app).get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_title_and_version_match_the_server(schema):
    from world_bank_api.config import SERVER_VERSION, TITLE

    assert schema["info"]["title"] == TITLE
    assert schema["info"]["version"] == SERVER_VERSION
