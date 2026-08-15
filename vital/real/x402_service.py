"""x402 service: VITAL sells an HTTP service and gets paid USDC per request.

This is the agent's most concrete real-income mechanism. It runs a small
FastAPI server whose endpoints are paywalled with the x402 protocol (HTTP 402
Payment Required). Any x402-capable client — human or another agent — pays
USDC on Base to call the endpoint, and VITAL records that as income.

Two facilitators:
    TEST (default)  -> https://x402.org/facilitator  (Base Sepolia, free test USDC)
    PROD            -> https://api.cdp.coinbase.com/platform/v2/x402 (Base mainnet, real USDC)

The service is built lazily so importing this module never requires fastapi or
x402 to be installed (demo mode stays dependency-free).

Endpoints offered (the agent's "products"):
    GET /vital/status   -> the agent's current vitals (balance, runway, mood)
    GET /vital/fortune  -> a short fortune/advice line
    GET /vital/echo     -> echo back a message (a trivial paid API)
"""

from __future__ import annotations

from typing import Optional

# Default facilitators (verified 2025).
TEST_FACILITATOR = "https://x402.org/facilitator"
PROD_FACILITATOR = "https://api.cdp.coinbase.com/platform/v2/x402"

DEFAULT_PRICE_USDC = "0.001"  # 0.001 USDC per request (micropayment)

# x402 v2 uses CAIP-2 network identifiers (eip155:<chainId>), NOT the friendly
# names used by cdp-sdk ("base"/"base-sepolia"). Map friendly -> CAIP-2.
#   Base mainnet  chainId 8453   -> eip155:8453
#   Base Sepolia  chainId 84532  -> eip155:84532
NETWORK_TO_CAIP2 = {
    "base": "eip155:8453",
    "base-mainnet": "eip155:8453",
    "eip155:8453": "eip155:8453",
    "base-sepolia": "eip155:84532",
    "eip155:84532": "eip155:84532",
}


def to_caip2(network: str) -> str:
    """Convert a friendly network name to the CAIP-2 id x402 v2 expects."""
    return NETWORK_TO_CAIP2.get(network, network)


def build_service(
    pay_to: str,
    price_usdc: str = DEFAULT_PRICE_USDC,
    network: str = "base-sepolia",
    facilitator_url: str = TEST_FACILITATOR,
    status_provider=None,
):
    """Build the FastAPI app with x402 paywalled endpoints.

    Args:
        pay_to: the wallet address that receives the USDC.
        price_usdc: price per request as a decimal string.
        network: "base-sepolia" (test) or "base" (mainnet).
        facilitator_url: facilitator to verify/settle payments.
        status_provider: optional callable returning a dict of agent vitals.

    Returns:
        A FastAPI app. Raises ImportError if fastapi/x402 are missing.
    """
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
    except ImportError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            "x402 service requires FastAPI: pip install fastapi 'x402[fastapi]'"
        ) from exc

    from x402 import x402ResourceServer
    from x402.http.facilitator_client import FacilitatorConfig, HTTPFacilitatorClient
    from x402.http.middleware.fastapi import payment_middleware
    from x402.mechanisms.evm.exact.register import register_exact_evm_server

    app = FastAPI(title="VITAL paid service", version="0.1.0")

    # x402 v2 needs CAIP-2 network ids (eip155:8453 / eip155:84532).
    caip2_network = to_caip2(network)

    # --- x402 resource server wired to the facilitator ---
    facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=facilitator_url))
    server = x402ResourceServer(facilitator)
    server = register_exact_evm_server(server, networks=[caip2_network])

    # Route config: which paths cost what. The default asset on these networks
    # is already USDC, so no explicit asset is needed.
    routes = {
        "/vital/*": {
            "accepts": [
                {
                    "scheme": "exact",
                    "network": caip2_network,
                    "payTo": pay_to,
                    "price": price_usdc,
                }
            ]
        }
    }

    # Record income when a payment settles.
    def _on_settled(ctx):
        try:
            amount = getattr(ctx, "amount", None)
            payer = getattr(ctx, "payer", "")
            if status_provider is not None:
                status_provider.on_x402_income(amount, payer)
        except Exception:
            pass

    try:
        server.on_after_settle(_on_settled)
    except Exception:
        pass

    app.middleware("http")(payment_middleware(routes, server))

    # --- Free endpoint: discovery / health ---
    @app.get("/")
    async def root():
        return {
            "service": "VITAL paid service",
            "paid_endpoints": ["/vital/status", "/vital/fortune", "/vital/echo"],
            "price_usdc": price_usdc,
            "network": network,
            "network_caip2": caip2_network,
            "pay_to": pay_to,
            "protocol": "x402",
        }

    # --- Paid endpoints ---
    @app.get("/vital/status")
    async def vital_status():
        if status_provider is not None:
            return status_provider.snapshot()
        return {"status": "ok"}

    @app.get("/vital/fortune")
    async def vital_fortune():
        import random

        fortunes = [
            "Earn more than you burn, and you will live forever.",
            "Your runway is only as long as your next paycheck.",
            "A saved credit is a second of life.",
            "The market pays the patient.",
            "Ship work, collect USDC, repeat.",
        ]
        return {"fortune": random.choice(fortunes)}

    @app.get("/vital/echo")
    async def vital_echo(request: Request):
        msg = request.query_params.get("msg", "")
        return {"echo": msg}

    return app


def run_service(
    host: str = "127.0.0.1",
    port: int = 8402,
    pay_to: str = "",
    price_usdc: str = DEFAULT_PRICE_USDC,
    network: str = "base-sepolia",
    facilitator_url: str = TEST_FACILITATOR,
    status_provider=None,
):
    """Run the x402 service with uvicorn (blocking)."""
    import uvicorn

    app = build_service(
        pay_to=pay_to,
        price_usdc=price_usdc,
        network=network,
        facilitator_url=facilitator_url,
        status_provider=status_provider,
    )
    uvicorn.run(app, host=host, port=port, log_level="info")
