from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Game, NewsItem


router = APIRouter()


@router.get("/{game_id}")
def get_news(
    game_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # Verify that the requested career exists.
    game = (
        db.query(Game)
        .filter(Game.id == game_id)
        .first()
    )

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found.",
        )

    news = (
        db.query(NewsItem)
        .filter(NewsItem.game_id == game_id)
        .order_by(
            NewsItem.career_day.desc(),
            NewsItem.game_hour.desc(),
            NewsItem.created_at.desc(),
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(item.id),
            "category": item.category,
            "priority": item.priority,
            "headline": item.headline,
            "body": item.body,
            "affected_symbol": item.affected_symbol,
            "affected_sector": item.affected_sector,
            "market_impact": item.market_impact,
            "career_day": item.career_day,
            "game_hour": item.game_hour,
            "is_read": item.is_read,
        }
        for item in news
    ]


@router.post("/{game_id}/mark-read/{news_id}")
def mark_read(
    game_id: str,
    news_id: str,
    db: Session = Depends(get_db),
):
    news = (
        db.query(NewsItem)
        .filter(
            NewsItem.id == news_id,
            NewsItem.game_id == game_id,
        )
        .first()
    )

    if news is None:
        raise HTTPException(
            status_code=404,
            detail="News item not found.",
        )

    news.is_read = True
    db.commit()
    db.refresh(news)

    return {
        "ok": True,
        "news_id": str(news.id),
        "is_read": news.is_read,
    }