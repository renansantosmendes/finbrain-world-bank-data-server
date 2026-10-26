"""Tests of the error responses: one body shape, one HTTP status per error class."""

from fastapi.testclient import TestClient

from world_bank_api.errors import InvalidRequestError, NotFoundError, UpstreamUnavailableError, WorldBankError
from world_bank_api.main import create_app, error_body, validation_message
from world_bank_api.dependencies import get_service
from world_bank_api.service import WorldBankService


def test_error_classes_map_to_their_statuses_and_codes():
    assert (InvalidRequestError("x").status_code, InvalidRequestError("x").code) == (400, "invalid_request")
    assert (NotFoundError("x").status_code, NotFoundError("x").code) == (404, "not_found")
    assert (UpstreamUnavailableError("x").status_code, UpstreamUnavailableError("x").code) == (502, "upstream_unavailable")
    assert (WorldBankError("x").status_code, WorldBankError("x").code) == (500, "internal_error")


def test_error_keeps_its_message():
    assert NotFoundError("No country matches the request.").message == "No country matches the request."


def test_error_body_has_exactly_code_and_message():
    assert error_body("not_found", "Nothing here.") == {"code": "not_found", "message": "Nothing here."}


def test_validation_message_names_the_parameter():
    message = validation_message({"loc": ("query", "freq"), "msg": "String should match pattern"})

    assert message == "freq: String should match pattern"


def test_validation_message_names_nested_body_fields():
    message = validation_message({"loc": ("body", "indicators"), "msg": "Field required"})

    assert message == "indicators: Field required"


def test_validation_message_without_location_uses_request():
    assert validation_message({"msg": "bad"}) == "request: bad"


def test_any_service_error_is_answered_with_its_status_and_body(gateway):
    class BrokenService(WorldBankService):
        def list_sources(self, source_id=None):
            raise UpstreamUnavailableError("The World Bank API could not be reached.")

    application = create_app()
    application.dependency_overrides[get_service] = lambda: BrokenService(gateway)
    response = TestClient(application).get("/sources")

    assert response.status_code == 502
    assert response.json() == {
        "code": "upstream_unavailable",
        "message": "The World Bank API could not be reached.",
    }


def test_invalid_parameter_is_a_400_with_the_shared_shape(client, gateway):
    response = client.get("/data/SP.POP.TOTL", params={"freq": "Q2"})

    assert response.status_code == 400
    body = response.json()
    assert set(body) == {"code", "message"}
    assert body["code"] == "invalid_request"
    assert body["message"].startswith("freq:")


def test_unknown_route_is_not_found(client):
    response = client.get("/no-such-route")

    assert response.status_code == 404
