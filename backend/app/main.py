"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.config import get_settings
from app.db.session import SessionLocal
from app.models.base import UserRole
from app.models.user import User
from app.services.auth import hash_password

settings = get_settings()

def ensure_bootstrap_admin() -> None:
    """Ensure the initial admin exists (configured via .env)."""
    if not settings.admin_email:
        return
    if not settings.admin_password:
        raise RuntimeError("ADMIN_EMAIL is set but ADMIN_PASSWORD is missing")

    db = SessionLocal()
    try:
        # If an active account already exists with this email, do nothing / fail fast.
        active = (
            db.query(User)
            .filter(User.email == settings.admin_email, User.deleted_at.is_(None))
            .first()
        )
        if active is not None:
            if active.role != UserRole.ADMIN:
                raise RuntimeError(
                    "Bootstrap admin email is already used by a non-admin active account. "
                    "Choose a different ADMIN_EMAIL."
                )
            return

        # No active account exists; create the bootstrap admin.
        user = User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            first_name=settings.admin_first_name,
            last_name=settings.admin_last_name,
            role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown (e.g. connect pools, run migrations)."""
    ensure_bootstrap_admin()
    yield
    # Shutdown: close pools if any

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if "*" in origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    def health():
        return {"status": "ok"}
        
    return app

app = create_app()