"""Dependency providers: how the routers receive their service.

Routers ask for ``get_service``; tests replace it with a service backed by a
fake gateway through FastAPI's ``dependency_overrides``.
"""

from functools import lru_cache

from fastapi import Depends

from world_bank_api.gateway import WorldBankGateway
from world_bank_api.service import WorldBankService


@lru_cache
def get_gateway() -> WorldBankGateway:
    """Return the gateway shared by the process.

    The gateway holds no data: it only has an uncached wbdata client, so one
    instance is enough for every request.

    Returns
    -------
    WorldBankGateway
        The gateway that calls the World Bank API.
    """
    return WorldBankGateway()


def get_service(gateway: WorldBankGateway = Depends(get_gateway)) -> WorldBankService:
    """Build the service the routers use for one request.

    Parameters
    ----------
    gateway : WorldBankGateway
        Gateway injected by FastAPI.

    Returns
    -------
    WorldBankService
        Service backed by the gateway.
    """
    return WorldBankService(gateway)
