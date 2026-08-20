# ===========================================================
# About the code
# ===========================================================
# This code is part of the project 'SpicePy'.
# See README.md for more details
#
# Licensed under the MIT license (see LICENCE)
# Copyright (c) 2017 Luca Giaccone (luca.giaccone@polito.it)
# ===========================================================

from dataclasses import dataclass
from enum import Enum, auto
from typing import Union


class ComponentType(Enum):
    RESISTOR = auto()
    INDUCTOR = auto()
    CAPACITOR = auto()
    VOLTAGE_SRC = auto()
    CURRENT_SRC = auto()
    VCVS = auto()
    CCCS = auto()
    VCCS = auto()
    CCVS = auto()


COMPONENT_TYPE_MAP: dict[str, ComponentType] = {
    'R': ComponentType.RESISTOR,
    'L': ComponentType.INDUCTOR,
    'C': ComponentType.CAPACITOR,
    'V': ComponentType.VOLTAGE_SRC,
    'I': ComponentType.CURRENT_SRC,
    'E': ComponentType.VCVS,
    'F': ComponentType.CCCS,
    'G': ComponentType.VCCS,
    'H': ComponentType.CCVS,
}


COMPONENT_UNITS: dict[int, dict[str, str]] = {
    0: {'voltage': 'W', 'current': 'W', 'power': 'W'},       # R
    1: {'voltage': 'W', 'current': 'W', 'power': 'W'},       # L
    2: {'voltage': 'W', 'current': 'W', 'power': 'W'},       # C
    3: {'voltage': 'W', 'current': 'W', 'power': 'W'},       # V (op)
    4: {'voltage': 'W', 'current': 'W', 'power': 'W'},       # I (op)
    5: {'voltage': 'W', 'current': 'W', 'power': 'W'},       # E
    6: {'voltage': 'W', 'current': 'W', 'power': 'W'},       # F
    7: {'voltage': 'W', 'current': 'W', 'power': 'W'},       # G
    8: {'voltage': 'W', 'current': 'W', 'power': 'W'},       # H
}

COMPONENT_UNITS_AC: dict[int, dict[str, str]] = {
    0: {'voltage': 'V', 'current': 'A', 'power': 'W'},       # R
    1: {'voltage': 'V', 'current': 'A', 'power': 'var'},     # L
    2: {'voltage': 'V', 'current': 'A', 'power': 'var'},     # C
    3: {'voltage': 'V', 'current': 'A', 'power': 'VA'},      # V
    4: {'voltage': 'V', 'current': 'A', 'power': 'VA'},      # I
    5: {'voltage': 'V', 'current': 'A', 'power': 'VA'},      # E
    6: {'voltage': 'V', 'current': 'A', 'power': 'VA'},      # F
    7: {'voltage': 'V', 'current': 'A', 'power': 'VA'},      # G
    8: {'voltage': 'V', 'current': 'A', 'power': 'VA'},      # H
}


def get_component_type(letter: str) -> ComponentType:
    """Return the ComponentType for a given letter prefix (R, L, C, V, I, E, F, G, H)."""
    ct = COMPONENT_TYPE_MAP.get(letter.upper())
    if ct is None:
        raise ValueError(f"Unknown component type: '{letter}'")
    return ct


def get_power_units(type_index: int, analysis: str) -> str:
    """Return the power unit string for a given component type index and analysis type."""
    if analysis == '.ac':
        return COMPONENT_UNITS_AC[type_index]['power']
    return COMPONENT_UNITS[type_index]['power']


@dataclass
class Component:
    """Represents a single circuit component."""
    name: str
    type: ComponentType
    nodes: tuple[int, int]
    value: Union[float, list, None] = None
    ic: Union[float, None] = None
    source_type: Union[str, None] = None
    control_source: Union[str, tuple, list, None] = None

    @property
    def letter(self) -> str:
        return self.name[0].upper()

    @property
    def number(self) -> int:
        return int(self.name[1:])
