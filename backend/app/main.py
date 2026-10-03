import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import monitor, plans
from app.config import settings
from app.payments.x402_setup import PaymentMiddlewareASGI, build_server, paid_routes
from app.services import monitor_agent, rag

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rag.build_index()
    monitor_agent.check_for_updates()  # snapshot inicial del corpus
    scheduler = monitor_agent.start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(title="Plan Contingencia API", lifespan=lifespan)

# x402 primero: el ultimo middleware agregado es el mas externo.
# CORS debe envolver al 402 para que el browser pueda leer la respuesta.
if settings.pay_to_address:
    app.add_middleware(
        PaymentMiddlewareASGI,
        routes=paid_routes(),
        server=build_server(),
    )
else:
    logging.warning("PAY_TO_ADDRESS no configurado: endpoints premium sin cobro x402")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plans.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")
