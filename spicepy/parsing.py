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
from typing import Union

import numpy as np

from .components import COMPONENT_TYPE_MAP, ComponentType

UNIT_PREFIX: dict[str, str] = {
    'meg': 'e6', 'f': 'e-15', 'p': 'e-12', 'n': 'e-9',
    'u': 'e-6', 'm': 'e-3', 'k': 'e3', 'g': 'e9', 't': 'e12',
}


def convert_unit(string_value: str) -> str:
    """Convert SPICE unit prefix to scientific notation string.

    Example: '10.5k' -> '10.5e3', '100meg' -> '100e6'
    """
    lower = string_value.lower()
    for prefix, value in UNIT_PREFIX.items():
        if prefix in lower:
            return lower.replace(prefix, value)
    return string_value


@dataclass
class NetlistData:
    """Container for all data extracted from a SPICE netlist file."""
    names: list[str]
    values: list[Union[float, list]]
    nodes: np.ndarray
    node_label2num: dict[str, int]
    node_num: int
    IC: dict[str, float]
    source_type: dict[str, str]
    control_source: dict[str, Union[str, list]]
    analysis: list[str]
    plot_cmd: Union[str, None]
    tf_cmd: Union[str, None]


def _parse_transient_source(line: str, source_name: str) -> list:
    """Parse a transient source line and return [type_str, params_list].

    For PWL returns [[type_str, [pairs]]].
    For others returns [type_str, [param1, param2, ...]].
    """
    index = line.lower().index(source_name)
    sline = line[:index].split()
    param = line[index:].replace('(', ' ').replace(')', ' ').split()
    sline.append(param[0])
    sline.append(param[1:])
    return sline


def _parse_component_line(line: str, analysis_type: str) -> list:
    """Parse a component line, handling transient sources.

    Returns a list: [name, node+, node-, value_or_params, ...]
    """
    if analysis_type == '.tran':
        time_sources = ['pwl', 'pulse', 'sin', 'exp']
        for source in time_sources:
            if source in line.lower():
                return _parse_transient_source(line, source)
    return line.split()


def _parse_value(sline: list[str], analysis: list[str],
                 source_type: dict, names: list, values: list,
                 node_labels: list, IC: dict, control_source: dict,
                 line_idx: int) -> None:
    """Parse a single component line and append to the lists."""
    name = sline[0]
    letter = name[0].upper()
    comp_type = COMPONENT_TYPE_MAP.get(letter)
    if comp_type is None:
        return

    if comp_type == ComponentType.RESISTOR:
        names.append(name)
        values.append(float(convert_unit(sline[3])))
        node_labels.append(sline[1:3])

    elif comp_type == ComponentType.INDUCTOR:
        names.append(name)
        values.append(float(convert_unit(sline[3])))
        node_labels.append(sline[1:3])
        if analysis[0] == '.tran':
            _parse_ic(name, sline, IC)

    elif comp_type == ComponentType.CAPACITOR:
        names.append(name)
        values.append(float(convert_unit(sline[3])))
        node_labels.append(sline[1:3])
        if analysis[0] == '.tran':
            _parse_ic(name, sline, IC)

    elif comp_type == ComponentType.CURRENT_SRC:
        names.append(name)
        node_labels.append(sline[1:3])
        if analysis[0] == '.ac' and len(sline) == 5:
            val = float(convert_unit(sline[3]))
            phase = float(sline[4]) * np.pi / 180
            values.append(val * (np.cos(phase) + np.sin(phase) * 1j))
        elif analysis[0] == '.tran':
            _parse_tran_source(name, sline, source_type, values)
        else:
            values.append(float(convert_unit(sline[3])))

    elif comp_type == ComponentType.VOLTAGE_SRC:
        names.append(name)
        node_labels.append(sline[1:3])
        if analysis[0] == '.ac' and len(sline) == 5:
            val = float(convert_unit(sline[3]))
            phase = float(sline[4]) * np.pi / 180
            values.append(val * (np.cos(phase) + np.sin(phase) * 1j))
        elif analysis[0] == '.tran':
            _parse_tran_source(name, sline, source_type, values)
        else:
            values.append(float(convert_unit(sline[3])))

    elif comp_type in (ComponentType.VCVS, ComponentType.VCCS):
        names.append(name)
        node_labels.append(sline[1:3])
        control_source[name] = sline[3:5]
        values.append(float(convert_unit(sline[5])))

    elif comp_type in (ComponentType.CCCS, ComponentType.CCVS):
        names.append(name)
        node_labels.append(sline[1:3])
        control_source[name] = sline[3]
        values.append(float(convert_unit(sline[4])))


def _parse_ic(name: str, sline: list[str], IC: dict) -> None:
    """Parse initial conditions for L or C components."""
    if len(sline) == 5:
        if sline[4].lower().find('ic') != -1:
            IC[name] = float(convert_unit(sline[4].split('=')[1]))
        else:
            raise ValueError(
                f"Warning: wrong definition of IC for {name} --> {sline[-1]}"
            )
    else:
        IC[name] = 0


def _parse_tran_source(name: str, sline: list[str],
                       source_type: dict, values: list) -> None:
    """Parse a transient source value (V or I) and append to values."""
    if isinstance(sline[-1], list):
        source_type[name] = sline[-2]
        if source_type[name] == 'pwl':
            values.append([[float(convert_unit(k)) for k in sline[-1]]])
        else:
            values.append([float(convert_unit(k)) for k in sline[-1]])
    else:
        values.append(float(convert_unit(sline[3])))


def parse_netlist(filename: str) -> NetlistData:
    """Parse a SPICE netlist file and return structured data.

    :param filename: path to the .net file
    :return: NetlistData with all parsed information
    """
    # first pass: extract analysis, plot_cmd, tf_cmd, component lines
    component_lines: list[str] = []
    analysis: Union[list[str], None] = None
    plot_cmd: Union[str, None] = None
    tf_cmd: Union[str, None] = None
    initials = set('VIRCELFGH')

    with open(filename) as f:
        for line in f:
            if ';' in line:
                line = line[:line.index(';')]
            if not line or line[0] == '*':
                continue
            if line[0].upper() in initials:
                component_lines.append(line.replace('\n', ''))
            elif line[0] == '.':
                line_clean = line.replace('\n', '')
                if '.end' in line_clean.lower():
                    break
                elif '.plot' in line_clean.lower():
                    plot_cmd = line_clean
                elif '.tf' in line_clean.lower():
                    tf_cmd = line_clean
                elif '.backanno' in line_clean.lower():
                    pass
                else:
                    analysis = line_clean.split()

    if analysis is None:
        raise ValueError("No analysis directive found in netlist")

    # second pass: parse each component
    names: list[str] = []
    values: list = []
    node_labels: list = []
    IC: dict[str, float] = {}
    source_type: dict[str, str] = {}
    control_source: dict[str, Union[str, list]] = {}

    for line in component_lines:
        sline = _parse_component_line(line, analysis[0])
        _parse_value(sline, analysis, source_type, names, values,
                     node_labels, IC, control_source, len(names))

    # remap node labels to numbers
    unique_labels, ii = np.unique(node_labels, return_inverse=True)
    if '0' not in unique_labels:
        raise ValueError("Error: the network does not include node '0'")

    nodes = np.reshape(ii, (len(node_labels), 2))
    node_label2num = {label: k for k, label in enumerate(np.unique(node_labels))}
    node_num = nodes.max()

    return NetlistData(
        names=names,
        values=values,
        nodes=nodes,
        node_label2num=node_label2num,
        node_num=node_num,
        IC=IC,
        source_type=source_type,
        control_source=control_source,
        analysis=analysis,
        plot_cmd=plot_cmd,
        tf_cmd=tf_cmd,
    )
