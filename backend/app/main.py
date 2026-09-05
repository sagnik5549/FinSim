"""
FastAPI main application — INVESTMENT BANKER MODE backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import game, market, portfolio, trade, news, career, performance
from app.database import Base, engine

# Create tables (Alembic handles migrations in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Investment Banker Mode — API",
    description="Backend for the Investment Banker Mode financial simulation game.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(game.router, prefix="/api/game", tags=["Game"])
app.include_router(market.router, prefix="/api/market", tags=["Market"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(trade.router, prefix="/api/trade", tags=["Trade"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(career.router, prefix="/api/career", tags=["Career"])
app.include_router(performance.router, prefix="/api/performance", tags=["Performance"])


@app.get("/health")
def health_check():
    return {"status": "ok", "game": "Investment Banker Mode"}
