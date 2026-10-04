"""
INVESTMENT BANKER MODE — FastAPI application.

The backend is authoritative for cash, prices, holdings, trade execution, time,
events and career outcomes. The frontend only renders state and sends intents.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import game, market, routes
from app.config import settings
from app.database.session import init_db
from app.services.game_service import NotFound
from app.simulation.game_engine import ActionError


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Investment Banker Mode API",
    description="Simulation backend for a financial career-management game. All market data is simulated.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ActionError)
async def action_error(_: Request, exc: ActionError):
    return JSONResponse(status_code=exc.status, content={"detail": {"code": exc.code, "message": exc.message}})


@app.exception_handler(NotFound)
async def not_found(_: Request, exc: NotFound):
    return JSONResponse(status_code=404, content={"detail": {"code": "NO_GAME", "message": "Game not found. Start a new career."}})


app.include_router(game.router, prefix="/api/game", tags=["Game"])
app.include_router(market.router, prefix="/api/market", tags=["Market"])
app.include_router(routes.portfolio, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(routes.trade, prefix="/api/trade", tags=["Trade"])
app.include_router(routes.opportunities, prefix="/api/opportunities", tags=["Opportunities"])
app.include_router(routes.research, prefix="/api/research", tags=["Research"])
app.include_router(routes.risk, prefix="/api/risk", tags=["Risk"])
app.include_router(routes.news, prefix="/api/news", tags=["News"])
app.include_router(routes.events, prefix="/api/events", tags=["Events"])
app.include_router(routes.career, prefix="/api/career", tags=["Career"])
app.include_router(routes.team, prefix="/api/team", tags=["Team"])
app.include_router(routes.performance, prefix="/api/performance", tags=["Performance"])
app.include_router(routes.leave, prefix="/api/leave", tags=["Leave"])


@app.get("/health")
def health():
    return {"status": "ok", "game": "Investment Banker Mode"}
