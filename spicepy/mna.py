# ===========================================================
# About the code
# ===========================================================
# This code is part of the project 'SpicePy'.
# See README.md for more details
#
# Licensed under the MIT license (see LICENCE)
# Copyright (c) 2017 Luca Giaccone (luca.giaccone@polito.it)
# ===========================================================

from typing import Callable

import numpy as np
from scipy.sparse import csr_matrix

from . import transient_sources as tsr

# ---------------------------------------------------------------------------
# Helpers used by multiple matrix builders
# ---------------------------------------------------------------------------

def _stamp_kclconductance(g, g_row, g_col, N1, N2, value, node_num, extra_col):
    """Stamp a conductance value into the MNA matrix (diagonal + off-diagonal)."""
    if N1 == 0:
        g.append(value)
        g_row.append(N2 - 1)
        g_col.append(N2 - 1)
    elif N2 == 0:
        g.append(value)
        g_row.append(N1 - 1)
        g_col.append(N1 - 1)
    else:
        g.append(value)
        g_row.append(N1 - 1)
        g_col.append(N1 - 1)
        g.append(value)
        g_row.append(N2 - 1)
        g_col.append(N2 - 1)
        g.append(-value)
        g_row.append(N1 - 1)
        g_col.append(N2 - 1)
        g.append(-value)
        g_row.append(N2 - 1)
        g_col.append(N1 - 1)


def _stamp_dynamic_capacitor(c, c_row, c_col, N1, N2, value):
    """Stamp a capacitor into the dynamic matrix."""
    if N1 == 0:
        c.append(value)
        c_row.append(N2 - 1)
        c_col.append(N2 - 1)
    elif N2 == 0:
        c.append(value)
        c_row.append(N1 - 1)
        c_col.append(N1 - 1)
    else:
        c.append(value)
        c_row.append(N1 - 1)
        c_col.append(N1 - 1)
        c.append(value)
        c_row.append(N2 - 1)
        c_col.append(N2 - 1)
        c.append(-value)
        c_row.append(N1 - 1)
        c_col.append(N2 - 1)
        c.append(-value)
        c_row.append(N2 - 1)
        c_col.append(N1 - 1)


def _stamp_extra_variable_source(g, g_row, g_col, N1, N2, extra_col):
    """Stamp the KCL equations for an extra-variable element (L, V, E, H).

    This stamps the +1/-1 terms connecting the branch current variable
    to the node equations.
    """
    if N1 == 0:
        g.append(-1)
        g_row.append(N2 - 1)
        g_col.append(extra_col)
        g.append(-1)
        g_row.append(extra_col)
        g_col.append(N2 - 1)
    elif N2 == 0:
        g.append(1)
        g_row.append(N1 - 1)
        g_col.append(extra_col)
        g.append(1)
        g_row.append(extra_col)
        g_col.append(N1 - 1)
    else:
        g.append(1)
        g_row.append(N1 - 1)
        g_col.append(extra_col)
        g.append(1)
        g_row.append(extra_col)
        g_col.append(N1 - 1)
        g.append(-1)
        g_row.append(N2 - 1)
        g_col.append(extra_col)
        g.append(-1)
        g_row.append(extra_col)
        g_col.append(N2 - 1)


def _find_vsens_index(names, isort, node_num, Vsens):
    """Find the extra-variable column index for a Vsens element.

    Vsens can be a V, E, or H source. Returns the column index in the
    MNA matrix where its current variable lives.
    """
    letter = Vsens[0].upper()
    if letter == 'V':
        h = sorted(isort[3]).index(names.index(Vsens))
        return node_num + len(isort[1]) + h
    elif letter == 'E':
        h = sorted(isort[5]).index(names.index(Vsens))
        return node_num + len(isort[1]) + len(isort[3]) + h
    elif letter == 'H':
        h = sorted(isort[8]).index(names.index(Vsens))
        return node_num + len(isort[1]) + len(isort[3]) + len(isort[5]) + h
    raise ValueError(f"Unknown Vsens type: {Vsens}")


# ---------------------------------------------------------------------------
# Matrix builders
# ---------------------------------------------------------------------------

def build_incidence_matrix(nodes: np.ndarray) -> csr_matrix:
    """Build the branch-to-node incidence matrix.

    :param nodes: (N_branches, 2) array of node pairs [N+, N-]
    :return: sparse incidence matrix A
    """
    a, a_row, a_col = [], [], []

    for b, (N1, N2) in enumerate(nodes):
        if N1 == 0:
            a.append(-1)
            a_row.append(N2 - 1)
            a_col.append(b)
        elif N2 == 0:
            a.append(1)
            a_row.append(N1 - 1)
            a_col.append(b)
        else:
            a.append(1)
            a_row.append(N1 - 1)
            a_col.append(b)
            a.append(-1)
            a_row.append(N2 - 1)
            a_col.append(b)

    return csr_matrix((a, (a_row, a_col)))


def build_conductance_matrix(
    names: list[str],
    values: list,
    nodes: np.ndarray,
    node_num: int,
    isort: list[list[int]],
    control_source: dict,
    node_label2num: dict[str, int],
) -> csr_matrix:
    """Build the MNA conductance/stamp matrix G.

    Handles: R, L (extra var), V (extra var), E/VCVS, F/CCCS, G/VCCS, H/CCVS.
    """
    g, g_row, g_col = [], [], []

    indexR = isort[0]
    indexL = sorted(isort[1])
    indexV = sorted(isort[3])
    indexE = sorted(isort[5])
    indexF = sorted(isort[6])
    indexG = sorted(isort[7])
    indexH = sorted(isort[8])

    # --- Resistors ---
    for ir in indexR:
        N1, N2 = nodes[ir]
        _stamp_kclconductance(g, g_row, g_col, N1, N2, 1.0 / values[ir], node_num, 0)

    # --- Inductors (extra variable) ---
    for k, il in enumerate(indexL):
        N1, N2 = nodes[il]
        _stamp_extra_variable_source(g, g_row, g_col, N1, N2, node_num + k)

    # --- Voltage sources (extra variable) ---
    for k, iv in enumerate(indexV):
        N1, N2 = nodes[iv]
        _stamp_extra_variable_source(g, g_row, g_col, N1, N2, node_num + len(indexL) + k)

    # --- VCVS (extra variable + gain terms) ---
    for k, ie in enumerate(indexE):
        N1, N2 = nodes[ie]
        extra_col = node_num + len(indexL) + len(indexV) + k
        _stamp_extra_variable_source(g, g_row, g_col, N1, N2, extra_col)

        # gain terms (control voltage)
        Nc1, Nc2 = [node_label2num[n] for n in control_source[names[ie]]]
        if Nc1 == 0:
            g.append(values[ie])
            g_row.append(extra_col)
            g_col.append(Nc2 - 1)
        elif Nc2 == 0:
            g.append(-values[ie])
            g_row.append(extra_col)
            g_col.append(Nc1 - 1)
        else:
            g.append(-values[ie])
            g_row.append(extra_col)
            g_col.append(Nc1 - 1)
            g.append(values[ie])
            g_row.append(extra_col)
            g_col.append(Nc2 - 1)

    # --- CCCS (current gain from Vsens) ---
    for indF in indexF:
        N1, N2 = nodes[indF]
        Vsens = control_source[names[indF]]
        n = _find_vsens_index(names, isort, node_num, Vsens)

        if N1 == 0:
            g.append(-values[indF])
            g_row.append(N2 - 1)
            g_col.append(n)
        elif N2 == 0:
            g.append(values[indF])
            g_row.append(N1 - 1)
            g_col.append(n)
        else:
            g.append(values[indF])
            g_row.append(N1 - 1)
            g_col.append(n)
            g.append(-values[indF])
            g_row.append(N2 - 1)
            g_col.append(n)

    # --- VCCS (voltage-controlled current source) ---
    for iG in indexG:
        N1, N2 = nodes[iG]
        Nc1, Nc2 = [node_label2num[n] for n in control_source[names[iG]]]

        if N1 != 0 and Nc1 != 0:
            g.append(values[iG])
            g_row.append(N1 - 1)
            g_col.append(Nc1 - 1)
        if N2 != 0 and Nc2 != 0:
            g.append(values[iG])
            g_row.append(N2 - 1)
            g_col.append(Nc2 - 1)
        if N1 != 0 and Nc2 != 0:
            g.append(-values[iG])
            g_row.append(N1 - 1)
            g_col.append(Nc2 - 1)
        if N2 != 0 and Nc1 != 0:
            g.append(-values[iG])
            g_row.append(N2 - 1)
            g_col.append(Nc1 - 1)

    # --- CCVS (extra variable + gain terms) ---
    for k, iH in enumerate(indexH):
        N1, N2 = nodes[iH]
        Vsens = control_source[names[iH]]
        n = _find_vsens_index(names, isort, node_num, Vsens)
        extra_col = node_num + len(indexL) + len(indexV) + len(indexE) + k

        if N1 != 0:
            g.append(1)
            g_row.append(N1 - 1)
            g_col.append(extra_col)
            g.append(1)
            g_row.append(extra_col)
            g_col.append(N1 - 1)
        if N2 != 0:
            g.append(-1)
            g_row.append(N2 - 1)
            g_col.append(extra_col)
            g.append(-1)
            g_row.append(extra_col)
            g_col.append(N2 - 1)

        g.append(-values[iH])
        g_row.append(extra_col)
        g_col.append(n)

    return csr_matrix((g, (g_row, g_col)))


def build_dynamic_matrix(
    values: list,
    nodes: np.ndarray,
    node_num: int,
    isort: list[list[int]],
    G_shape: tuple,
) -> csr_matrix:
    """Build the dynamic matrix C for energy-storage elements (L and C)."""
    c, c_row, c_col = [], [], []

    indexL = sorted(isort[1])
    indexC = isort[2]

    # --- Inductors ---
    for k, il in enumerate(indexL):
        c.append(-values[il])
        c_row.append(node_num + k)
        c_col.append(node_num + k)

    # --- Capacitors ---
    for ic in indexC:
        N1, N2 = nodes[ic]
        _stamp_dynamic_capacitor(c, c_row, c_col, N1, N2, values[ic])

    return csr_matrix((c, (c_row, c_col)), shape=G_shape)


def build_rhs_static(
    values: list,
    nodes: np.ndarray,
    node_num: int,
    isort: list[list[int]],
) -> np.ndarray:
    """Build the static RHS vector for .op / .ac analysis."""
    rhs = [0] * (node_num + len(isort[1]) + len(isort[3]) + len(isort[5]) + len(isort[8]))

    NL = len(isort[1])
    indexV = sorted(isort[3])
    indexI = isort[4]

    for k, iv in enumerate(indexV):
        rhs[node_num + NL + k] += values[iv]

    for ii in indexI:
        N1, N2 = nodes[ii]
        if N1 == 0:
            rhs[N2 - 1] += values[ii]
        elif N2 == 0:
            rhs[N1 - 1] -= values[ii]
        else:
            rhs[N1 - 1] -= values[ii]
            rhs[N2 - 1] += values[ii]

    return np.array(rhs)


def build_rhs_transient(
    names: list[str],
    values: list,
    nodes: np.ndarray,
    node_num: int,
    isort: list[list[int]],
    source_type: dict[str, str],
) -> Callable[[float], np.ndarray]:
    """Build the time-varying RHS closure for .tran analysis.

    Returns a function fun(t) -> rhs_vector.
    """
    NL = len(isort[1])
    indexV = sorted(isort[3])
    indexI = isort[4]

    def fun(t: float) -> np.ndarray:
        rhs = [0] * (node_num + NL + len(isort[3]) + len(isort[5]) + len(isort[8]))

        for k, iv in enumerate(indexV):
            if isinstance(values[iv], list):
                tsr_fun = getattr(tsr, source_type[names[iv]])
                rhs[node_num + NL + k] += tsr_fun(*values[iv], t=t)
            else:
                rhs[node_num + NL + k] += values[iv]

        for ii in indexI:
            N1, N2 = nodes[ii]
            if isinstance(values[ii], list):
                tsr_fun = getattr(tsr, source_type[names[ii]])
                val = tsr_fun(*values[ii], t=t)
            else:
                val = values[ii]

            if N1 == 0:
                rhs[N2 - 1] += val
            elif N2 == 0:
                rhs[N1 - 1] -= val
            else:
                rhs[N1 - 1] -= val
                rhs[N2 - 1] += val

        return np.array(rhs)

    return fun
