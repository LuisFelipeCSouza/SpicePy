# ===========================================================
# About the code
# ===========================================================
# This code is part of the project 'SpicePy'.
# See README.md for more details
#
# Licensed under the MIT license (see LICENCE)
# Copyright (c) 2017 Luca Giaccone (luca.giaccone@polito.it)
# ===========================================================

from typing import Union

import numpy as np
from scipy.sparse import csr_matrix

from . import transient_sources as tsr


def compute_branch_voltage(A: 'csr_matrix', x: np.ndarray, node_num: int) -> np.ndarray:
    """Compute branch voltages from node voltages.

    :param A: incidence matrix
    :param x: solution vector (node voltages + extra variables)
    :param node_num: number of nodes
    :return: branch voltage array
    """
    return A.transpose() * x[:node_num, ...]


def compute_branch_current(
    names: list[str],
    values: list,
    nodes: np.ndarray,
    node_num: int,
    isort: list[list[int]],
    control_source: dict,
    vb: np.ndarray,
    x: np.ndarray,
    analysis: list[str],
    source_type: dict[str, str] = None,
    f: Union[float, np.ndarray, None] = None,
    t: Union[np.ndarray, None] = None,
    node_label2num: dict[str, int] = None,
) -> np.ndarray:
    """Compute branch currents for all components.

    :return: branch current array (same shape as vb)
    """
    ib = np.zeros_like(vb)

    for k, name in enumerate(names):
        ib[k, ...] = get_current(
            name, names, values, nodes, node_num, isort,
            control_source, x, analysis, source_type, f, t,
            node_label2num,
        )

    return ib


def get_current(
    name: str,
    names: list[str],
    values: list,
    nodes: np.ndarray,
    node_num: int,
    isort: list[list[int]],
    control_source: dict,
    x: np.ndarray,
    analysis: list[str],
    source_type: dict[str, str] = None,
    f: Union[float, np.ndarray, None] = None,
    t: Union[np.ndarray, None] = None,
    node_label2num: dict[str, int] = None,
) -> np.ndarray:
    """Get the current through a single component.

    :param name: component name (e.g. 'R1', 'V2')
    :return: current value(s)
    """
    letter = name[0].upper()
    idx = names.index(name)

    # Resistor or Capacitor
    if letter in ('R', 'C'):
        v = get_voltage(name, names, nodes, node_num, x, analysis, f, t, node_label2num)
        if letter == 'R':
            return v / values[idx]
        else:
            if analysis[0].lower() == '.tran':
                from scipy.interpolate import CubicSpline
                cs = CubicSpline(t, v)
                csd = cs.derivative()
                return values[idx] * csd(t)
            elif analysis[0].lower() == '.ac':
                Xc = -1.0 / (2 * np.pi * f * values[idx])
                return v / (Xc * 1j)
            return np.zeros_like(v) if not np.isscalar(v) else 0.0

    # Inductor
    if letter == 'L':
        h = sorted(isort[1]).index(names.index(name))
        n = node_num + h
        return x[n, ...]

    # Voltage source
    if letter == 'V':
        h = sorted(isort[3]).index(names.index(name))
        n = node_num + len(isort[1]) + h
        return x[n, ...]

    # Current source
    if letter == 'I':
        if isinstance(values[idx], list) and source_type:
            tsr_fun = getattr(tsr, source_type[name])
            return tsr_fun(*values[idx], t)
        return values[idx]

    # VCVS
    if letter == 'E':
        h = sorted(isort[5]).index(names.index(name))
        n = node_num + len(isort[1]) + len(isort[3]) + h
        return x[n, ...]

    # CCCS
    if letter == 'F':
        vsens_name = control_source[name]
        return get_current(vsens_name, names, values, nodes, node_num, isort,
                          control_source, x, analysis, source_type, f, t,
                          node_label2num) * values[names.index(name)]

    # VCCS
    if letter == 'G':
        ctrl = control_source[name]
        return values[names.index(name)] * get_voltage(
            ctrl, names, nodes, node_num, x, analysis, f, t, node_label2num,
        )

    # CCVS
    if letter == 'H':
        h = sorted(isort[8]).index(names.index(name))
        n = node_num + len(isort[1]) + len(isort[3]) + len(isort[5]) + h
        return x[n, ...]

    return 0.0


def get_voltage(
    arg: Union[str, list],
    names: list[str],
    nodes: np.ndarray,
    node_num: int,
    x: np.ndarray,
    analysis: list[str],
    f: Union[float, np.ndarray, None] = None,
    t: Union[np.ndarray, None] = None,
    node_label2num: dict[str, int] = None,
) -> np.ndarray:
    """Compute voltage across components or between node pairs.

    :param arg: string like 'R1 C1 (2,3)' or list like [[2,3],[3,0]]
    :return: voltage array
    """
    if isinstance(arg, str):
        voltage_list = arg.split()
    else:
        if not isinstance(arg[0], list):
            arg = [arg]
        voltage_list = None  # handled separately

    # determine output shape
    if analysis[0].lower() == '.tran' and t is not None:
        rows = len(voltage_list) if voltage_list else len(arg)
        v = np.zeros((rows, t.size), dtype=x.dtype)
    elif analysis[0].lower() == '.ac' and f is not None and not np.isscalar(f):
        rows = len(voltage_list) if voltage_list else len(arg)
        v = np.zeros((rows, f.size), dtype=x.dtype)
    else:
        rows = len(voltage_list) if voltage_list else len(arg)
        v = np.zeros(rows, dtype=x.dtype)

    if voltage_list is not None:
        for k, variable in enumerate(voltage_list):
            v[k, ...] = _voltage_for_term(variable, names, nodes, node_num, x, node_label2num)
    else:
        for k, node_labels in enumerate(arg):
            v[k, ...] = _voltage_for_pair(node_labels, names, nodes, node_num, x, node_label2num)

    if len(v.shape) == 2 and v.shape[0] == 1:
        v = v.flatten()
    return v


def _voltage_for_term(
    variable: str,
    names: list[str],
    nodes: np.ndarray,
    node_num: int,
    x: np.ndarray,
    node_label2num: dict[str, int],
) -> np.ndarray:
    """Get voltage for a single term (component name or node pair string)."""
    for char in ('(', ')'):
        variable = variable.replace(char, '')

    if variable in names:
        idx = names.index(variable)
        nodelist = [n - 1 for n in nodes[idx] if n != 0]
        if len(nodelist) == 2:
            return x[nodelist[0], ...] - x[nodelist[1], ...]
        else:
            sign = 1 if nodes[idx][0] != 0 else -1
            return x[nodelist[0], ...] * sign
    else:
        node_labels = variable.split(',')
        node_number = [node_label2num[k] for k in node_labels]
        nodelist = [int(k) - 1 for k in node_number if k != 0]
        if len(nodelist) == 2:
            return x[nodelist[0], ...] - x[nodelist[1], ...]
        else:
            sign = 1 if node_number[0] != 0 else -1
            return x[nodelist[0], ...] * sign


def _voltage_for_pair(
    node_labels: list,
    names: list[str],
    nodes: np.ndarray,
    node_num: int,
    x: np.ndarray,
    node_label2num: dict[str, int],
) -> np.ndarray:
    """Get voltage for a node pair list [n1, n2]."""
    node_number = [node_label2num[str(k)] for k in node_labels]
    nodelist = [int(k) - 1 for k in node_number if k != 0]

    if len(nodelist) == 2:
        return x[nodelist[0], ...] - x[nodelist[1], ...]
    else:
        sign = 1 if node_number[0] != 0 else -1
        return x[nodelist[0], ...] * sign


def compute_branch_power(vb: np.ndarray, ib: np.ndarray, analysis: str) -> np.ndarray:
    """Compute branch power.

    :return: real power for .op/.tran, complex power for .ac
    """
    if analysis.lower() == '.ac':
        return vb * np.conj(ib)
    return vb * ib
