"""Shared pytest fixtures.

Integration tests use an in-memory SQLite database. The pgvector-backed tables
(`documents`, `document_chunks`) are excluded from the test schema because
SQLite has no `vector` type. Anything RAG-related is therefore out of scope
for the integration suite.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
# Force all model modules to register against Base.metadata before we prune.
import app.models  # noqa: F401
from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.base import PartType, UserRole
from app.models.build import Build, BuildPart
from app.models.component import (
    CPU,
    GPU,
    PSU,
    Case,
    CaseFan,
    CPUCooler,
    Memory,
    Mobo,
    Storage,
)
from app.models.thread import Message, Thread
from app.models.user import User
from app.services.auth import create_access_token, hash_password

# pgvector tables cannot be created on SQLite; remove them before create_all.
for _pg_only in ("document_chunks", "documents"):
    if _pg_only in Base.metadata.tables:
        Base.metadata.remove(Base.metadata.tables[_pg_only])


# ---------------------------------------------------------------------------
# Engine / session plumbing
# ---------------------------------------------------------------------------
@pytest.fixture
def engine():
    """Fresh in-memory SQLite per test — no state bleed between tests."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(bind=eng)
        eng.dispose()


@pytest.fixture
def TestSession(engine):
    """Session factory bound to the test engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def db_session(TestSession) -> Iterator[Session]:
    """A short-lived session for seeding test data outside of API calls."""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# FastAPI client with DB + LLM overrides
# ---------------------------------------------------------------------------
@pytest.fixture
def client(TestSession, monkeypatch) -> Iterator[TestClient]:
    """A TestClient with:
    - `get_db` overridden to use the in-memory SQLite engine
    - `generate_chat_reply` stubbed so tests never hit Gemini
    - `ensure_bootstrap_admin` neutralised so tests don't need a real DB on import
    """

    def _override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    # Defend against accidental lifespan invocations (not triggered by default
    # unless the test uses `with TestClient(...) as c:`, but cheap to guard).
    monkeypatch.setattr("app.main.ensure_bootstrap_admin", lambda: None)

    # Replace the LLM entrypoint at the import site the endpoint uses.
    def _fake_reply(*_args, user_request: str = "", **_kwargs) -> str:
        return f"[stub reply to: {user_request[:40]}]"

    monkeypatch.setattr(
        "app.api.v1.endpoints.messages.generate_chat_reply",
        _fake_reply,
    )

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# User / auth fixtures
# ---------------------------------------------------------------------------
def _make_user(session: Session, *, email: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        email=email,
        password_hash=hash_password("password123"),
        first_name="Test",
        last_name="User",
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def user(db_session) -> User:
    return _make_user(db_session, email="user@example.com", role=UserRole.USER)


@pytest.fixture
def other_user(db_session) -> User:
    return _make_user(db_session, email="other@example.com", role=UserRole.USER)


@pytest.fixture
def admin(db_session) -> User:
    return _make_user(db_session, email="admin@example.com", role=UserRole.ADMIN)


def _bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user)}"}


@pytest.fixture
def user_headers(user) -> dict[str, str]:
    return _bearer(user)


@pytest.fixture
def other_user_headers(other_user) -> dict[str, str]:
    return _bearer(other_user)


@pytest.fixture
def admin_headers(admin) -> dict[str, str]:
    return _bearer(admin)


# ---------------------------------------------------------------------------
# Catalog seed (shared across build/catalog tests)
# ---------------------------------------------------------------------------
@pytest.fixture
def seeded_catalog(db_session) -> dict[str, object]:
    """Minimal one-of-each catalog for tests that need real component IDs."""
    cpu1 = CPU(name="Test CPU 1", core_count=8, price=Decimal("299.99"))
    cpu2 = CPU(name="Test CPU 2", core_count=16, price=Decimal("599.00"))
    gpu1 = GPU(name="Test GPU 1", chipset="RTX 4070", memory="12GB", price=Decimal("599.99"))
    gpu2 = GPU(name="Test GPU 2", chipset="RX 7800", memory="16GB", price=Decimal("499.00"))
    mobo = Mobo(name="Test Mobo", form_factor="ATX", price=Decimal("199.99"))
    memory = Memory(name="Test RAM", speed="DDR5-6000", modules="2x16GB", price=Decimal("129.99"))
    case = Case(name="Test Case", type="ATX Mid Tower", price=Decimal("89.99"))
    storage = Storage(
        name="Test SSD",
        capacity="2TB",
        type="SSD",
        form_factor="M.2",
        interface="PCIe 4.0",
        price=Decimal("149.99"),
    )
    cooler = CPUCooler(name="Test Cooler", price=Decimal("69.99"))
    psu = PSU(name="Test PSU", type="ATX", wattage="850W", price=Decimal("139.99"))
    fan = CaseFan(name="Test Fan", size="120mm", price=Decimal("19.99"))
    db_session.add_all([cpu1, cpu2, gpu1, gpu2, mobo, memory, case, storage, cooler, psu, fan])
    db_session.commit()
    for obj in (cpu1, cpu2, gpu1, gpu2, mobo, memory, case, storage, cooler, psu, fan):
        db_session.refresh(obj)
    return {
        "cpu1": cpu1,
        "cpu2": cpu2,
        "gpu1": gpu1,
        "gpu2": gpu2,
        "mobo": mobo,
        "memory": memory,
        "case": case,
        "storage": storage,
        "cooler": cooler,
        "psu": psu,
        "fan": fan,
    }


# ---------------------------------------------------------------------------
# Small helpers re-exported for test readability
# ---------------------------------------------------------------------------
__all__ = [
    "PartType",
    "UserRole",
    "User",
    "Thread",
    "Message",
    "Build",
    "BuildPart",
]