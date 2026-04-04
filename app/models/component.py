"""Hardware component models (catalog tables)."""

from decimal import Decimal
from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base  # noqa: F401 - used by all component tables

class Mobo(Base):
    __tablename__ = "mobo"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    socket: Mapped[str | None] = mapped_column(String(50), nullable=True)
    form_factor: Mapped[str] = mapped_column(String(50), nullable=False)
    memory_max: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memory_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

class CPU(Base):
    __tablename__ = "cpu"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    core_count: Mapped[int] = mapped_column(Integer, nullable=False)
    perf_clock: Mapped[str | None] = mapped_column(String(100), nullable=True)
    boost_clock: Mapped[str | None] = mapped_column(String(100), nullable=True)
    microarch: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tdp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    graphics: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

class Memory(Base):
    __tablename__ = "memory"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    speed: Mapped[str] = mapped_column(String(100), nullable=False)
    modules: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_word_latency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cas_latency: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

class Case(Base):
    __tablename__ = "case"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    power_supply: Mapped[str | None] = mapped_column(String(100), nullable=True)
    side_panel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_volume: Mapped[str | None] = mapped_column(String(100), nullable=True)
    internal_bays: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

class Storage(Base):
    __tablename__ = "storage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    capacity: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    cache: Mapped[str | None] = mapped_column(String(100), nullable=True)
    form_factor: Mapped[str] = mapped_column(String(50), nullable=False)
    interface: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

class CPUCooler(Base):
    __tablename__ = "cpu_cooler"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    fan_rpm: Mapped[str | None] = mapped_column(String(100), nullable=True)
    noise_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    radiator_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

class PSU(Base):
    __tablename__ = "psu"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    efficiency_rating: Mapped[str | None] = mapped_column(String(50), nullable=True)
    wattage: Mapped[str] = mapped_column(String(100), nullable=False)
    modular: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

class CaseFan(Base):
    __tablename__ = "case_fans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    size: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rpm: Mapped[str | None] = mapped_column(String(100), nullable=True)
    airflow: Mapped[str | None] = mapped_column(String(100), nullable=True)
    noise_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pwm: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

class GPU(Base):
    __tablename__ = "gpu"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    chipset: Mapped[str] = mapped_column(String(100), nullable=False)
    memory: Mapped[str] = mapped_column(String(100), nullable=False)
    core_clock: Mapped[str | None] = mapped_column(String(100), nullable=True)
    boost_clock: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    length: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)