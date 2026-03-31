"""Catalog response schemas -- one per component type."""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class _ComponentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    price: Decimal

class MoboOut(_ComponentBase):
    name: str
    socket: str | None
    form_factor: str
    memory_max: int | None
    memory_slot: int | None
    color: str | None

class CPUOut(_ComponentBase):
    name: str
    core_count: int
    perf_clock: Decimal | None
    boost_clock: Decimal | None
    microarch: str | None
    tdp: int | None
    graphics: str | None

class MemoryOut(_ComponentBase):
    name: str
    speed: int
    modules: int
    color: str | None
    first_word_latency: Decimal | None
    cas_latency: Decimal | None

class CaseOut(_ComponentBase):
    name: str
    type: str
    color: str | None
    power_supply: str | None
    side_panel: str | None
    volume: Decimal | None
    bays: int | None

class StorageOut(_ComponentBase):
    name: str
    capacity: int
    type: str
    cache: int | None
    form_factor: str
    interface: str

class CPUCoolerOut(_ComponentBase):
    name: str
    fan_rpm: int | None
    noise_level: Decimal | None
    color: str | None
    radiator_size: int | None

class PSUOut(_ComponentBase):
    name: str
    type: str
    efficiency: str | None
    wattage: int
    modular: bool | None
    color: str | None

class CaseFanOut(_ComponentBase):
    name: str
    size: int
    color: str | None
    rpm: int | None
    airflow: Decimal | None
    noise_level: Decimal | None
    pwm: bool | None

class GPUOut(_ComponentBase):
    name: str
    chipset: str
    memory: int
    core_clock: Decimal | None
    boost_clock: Decimal | None
    color: str | None
    length: Decimal | None