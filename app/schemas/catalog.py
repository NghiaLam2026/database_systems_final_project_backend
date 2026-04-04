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
    memory_max: str | None
    memory_slot: int | None
    color: str | None

class CPUOut(_ComponentBase):
    name: str
    core_count: int
    perf_clock: str | None
    boost_clock: str | None
    microarch: str | None
    tdp: str | None
    graphics: str | None

class MemoryOut(_ComponentBase):
    name: str
    speed: str
    modules: str
    color: str | None
    first_word_latency: str | None
    cas_latency: Decimal | None

class CaseOut(_ComponentBase):
    name: str
    type: str
    color: str | None
    power_supply: str | None
    side_panel: str | None
    external_volume: str | None
    internal_bays: int | None

class StorageOut(_ComponentBase):
    name: str
    capacity: str
    type: str
    cache: str | None
    form_factor: str
    interface: str

class CPUCoolerOut(_ComponentBase):
    name: str
    fan_rpm: str | None
    noise_level: str | None
    color: str | None
    radiator_size: str | None


class PSUOut(_ComponentBase):
    name: str
    type: str
    efficiency_rating: str | None
    wattage: str
    modular: bool | None
    color: str | None


class CaseFanOut(_ComponentBase):
    name: str
    size: str
    color: str | None
    rpm: str | None
    airflow: str | None
    noise_level: str | None
    pwm: bool | None


class GPUOut(_ComponentBase):
    name: str
    chipset: str
    memory: str
    core_clock: str | None
    boost_clock: str | None
    color: str | None
    length: str | None