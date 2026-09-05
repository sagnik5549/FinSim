from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import game_service
from app.models.db_models import NewsItem, Game

router = APIRouter()


@router.get("/{game_id}")
def get_news(game_id: str, limit: int = 20, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")
    news = (
        db.query(NewsItem)
        .filter(NewsItem.game_id == game_id)
        .order_by(NewsItem.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(n.id), "category": n.category, "priority": n.priority,
            "headline": n.headline, "body": n.body,
            "affected_symbol": n.affected_symbol, "affected_sector": n.affected_sector,
            "market_impact": n.market_impact, "career_day": n.career_day,
            "game_hour": n.game_hour, "is_read": n.is_read,
        }
        for n in news
    ]


@router.post("/{game_id}/mark-read/{news_id}")
def mark_read(game_id: str, news_id: str, db: Session = Depends(get_db)):
    news = db.query(NewsItem).filter(NewsItem.id == news_id, NewsItem.game_id == game_id).first()
    if news:
        news.is_read = True
        db.commit()
    return {"ok": True}
