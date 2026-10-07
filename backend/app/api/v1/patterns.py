from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.engine.pattern_archive import load_extra_auth_keywords, add_extra_auth_keyword

router = APIRouter(prefix="/patterns", tags=["Pattern Archive"])


class AuthKeywordRequest(BaseModel):
    keyword: str = Field(...)


@router.get("/auth-keywords", response_model=dict)
async def list_auth_keywords(db: AsyncSession = Depends(get_db_session)):
    return {"keywords": await load_extra_auth_keywords(db)}


@router.post("/auth-keywords", response_model=dict)
async def add_auth_keyword(payload: AuthKeywordRequest, db: AsyncSession = Depends(get_db_session)):
    keywords = await add_extra_auth_keyword(payload.keyword, db)
    return {"keywords": keywords}
