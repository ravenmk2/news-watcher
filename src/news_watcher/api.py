"""FastAPI 路由（当前仅健康检查，后续按需扩展）。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
