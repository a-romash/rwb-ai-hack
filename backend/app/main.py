import asyncio
import logging
from contextlib import asynccontextmanager

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_session
from app.projects import router
from app.runs import router as runs_router

@asynccontextmanager
async def lifespan(app):
    async def watch():
        from app.runner import reconcile
        while True:
            await asyncio.sleep(10)
            try:
                await asyncio.to_thread(reconcile)
            except Exception:
                logging.exception("Не удалось повторно отправить задачи")
    watcher = asyncio.create_task(watch())
    try:
        yield
    finally:
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan, title="Менеджер ИИ-пайплайна", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
app.include_router(router, prefix="/api")
app.include_router(runs_router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health(session: Annotated[Session, Depends(get_session)]):
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "База данных недоступна") from None
    return {"status": "ok"}
