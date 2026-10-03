"""Configuracion de x402 v2 sobre Monad.

El facilitador de Monad solo soporta x402 v2. El USDC de testnet no esta en
la tabla de assets del SDK, asi que registramos un money parser que mapea
montos decimales a unidades atomicas (6 decimales) del token.
"""
from decimal import Decimal

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import Network
from x402.schemas.base import AssetAmount
from x402.server import x402ResourceServer

from app.config import settings

MONAD_NETWORK: Network = settings.monad_network  # eip155:10143


def build_server() -> x402ResourceServer:
    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(url=settings.x402_facilitator_url)
    )
    server = x402ResourceServer(facilitator)

    scheme = ExactEvmServerScheme()

    # Los money parsers se ejecutan sincronicamente y reciben el monto como
    # string decimal ("0.01"). Deben devolver AssetAmount o None.
    def monad_money_parser(amount, network: str):
        if network == str(MONAD_NETWORK):
            return AssetAmount(
                amount=str(int(Decimal(str(amount)) * 1_000_000)),  # USDC: 6 dec.
                asset=settings.monad_usdc_address,
                extra={"name": "USDC", "version": "2"},
            )
        return None

    scheme.register_money_parser(monad_money_parser)

    server.register(MONAD_NETWORK, scheme)
    return server


def paid_routes() -> dict[str, RouteConfig]:
    """Endpoints premium protegidos por micropago."""
    return {
        "POST /plans/generate-premium": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=settings.pay_to_address,
                    price="$0.01",
                    network=MONAD_NETWORK,
                )
            ],
            mime_type="application/json",
            description="Generacion de plan de contingencia premium con citas legales",
        ),
        "POST /plans/update-premium": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=settings.pay_to_address,
                    price="$0.005",
                    network=MONAD_NETWORK,
                )
            ],
            mime_type="application/json",
            description="Actualizacion de plan ante cambio normativo",
        ),
    }


__all__ = ["build_server", "paid_routes", "PaymentMiddlewareASGI"]
