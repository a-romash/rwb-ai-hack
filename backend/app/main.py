from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_session
from app.projects import router

app = FastAPI(title="Менеджер ИИ-пайплайна", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
app.include_router(router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health(session: Annotated[Session, Depends(get_session)]):
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "База данных недоступна") from None
    return {"status": "ok"}
