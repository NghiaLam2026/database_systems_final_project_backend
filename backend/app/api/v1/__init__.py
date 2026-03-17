"""API v1 routes."""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, builds, threads, messages, catalog

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(builds.router, prefix="/builds", tags=["builds"])
api_router.include_router(threads.router, prefix="/threads", tags=["threads"])
api_router.include_router(messages.router, prefix="/threads", tags=["messages"])
api_router.include_router(catalog.router, prefix="/catalog", tags=["catalog"])