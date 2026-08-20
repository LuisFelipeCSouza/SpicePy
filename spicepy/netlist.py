# ===========================================================
# About the code
# ===========================================================
# This code is part of the project 'SpicePy'.
# See README.md for more details
#
# Licensed under the MIT license (see LICENCE)
# Copyright (c) 2017 Luca Giaccone (luca.giaccone@polito.it)
# ===========================================================

from __future__ import annotations

from typing import Union

import numpy as np

from .display import plot_bode, plot_transient, print_results
from .mna import (
    build_conductance_matrix,
    build_dynamic_matrix,
    build_incidence_matrix,
    build_rhs_static,
    build_rhs_transient,
)
from .parsing import NetlistData, convert_unit, parse_netlist
from .results import (
    compute_branch_current,
    compute_branch_power,
    compute_branch_voltage,
    get_current,
    get_voltage,
)


class Network:
    """Container for a SPICE circuit network.

    Can be created from a netlist file or from explicit parameters::

        # From file
        net = Network('circuit.net')

        # From parts
        net = Network.from_parts(
            names=['R1', 'V1'],
            values=[1000.0, 5.0],
            nodes=np.array([[1, 0], [1, 0]]),
            analysis=['.op'],
        )
    """

    def __init__(self, filename: str | None = None, **kwargs):
        """Create a Network.

        :param filename: path to a SPICE netlist file (optional if using kwargs)
        :param kwargs: explicit network data (see from_parts)
        """
        if filename is not None:
            data = parse_netlist(filename)
            self.names = data.names
            self.values = data.values
            self.IC = data.IC
            self.source_type = data.source_type
            self.control_source = data.control_source
            self.nodes = data.nodes
            self.node_label2num = data.node_label2num
            self.node_num = data.node_num
            self.analysis = data.analysis
            self.plot_cmd = data.plot_cmd
            self.tf_cmd = data.tf_cmd
        else:
            self._init_from_parts(**kwargs)

        # mutable state (populated by solve / matrix methods)
        self.A = None
        self.G = None
        self.C = None
        self.rhs = None
        self.isort = None
        self.t = None
        self.f = None
        self.x = None
        self.vb = None
        self.ib = None
        self.pb = None

    # ------------------------------------------------------------------
    # Construction from parts
    # ------------------------------------------------------------------

    def _init_from_parts(
        self,
        names: list[str],
        values: list,
        nodes: np.ndarray,
        analysis: list[str],
        node_label2num: dict[str, int] | None = None,
        IC: dict[str, float] | None = None,
        source_type: dict[str, str] | None = None,
        control_source: dict | None = None,
        plot_cmd: str | None = None,
        tf_cmd: str | None = None,
    ) -> None:
        """Initialize network attributes from explicit data."""
        self.names = list(names)
        self.values = list(values)
        self.nodes = np.asarray(nodes)
        self.analysis = list(analysis)
        self.IC = IC or {}
        self.source_type = source_type or {}
        self.control_source = control_source or {}
        self.plot_cmd = plot_cmd
        self.tf_cmd = tf_cmd

        # auto-build node mapping if not provided
        if node_label2num is not None:
            self.node_label2num = dict(node_label2num)
        else:
            unique = np.unique(self.nodes)
            self.node_label2num = {str(int(k)): int(k) for k in unique}

        self.node_num = int(self.nodes.max())

    @classmethod
    def from_parts(
        cls,
        names: list[str],
        values: list,
        nodes: np.ndarray,
        analysis: list[str],
        **kwargs,
    ) -> "Network":
        """Create a Network from explicit component data.

        :param names: component names (e.g. ['R1', 'V1'])
        :param values: component values (e.g. [1000.0, 5.0])
        :param nodes: (N, 2) array of node pairs [N+, N-] (node 0 = ground)
        :param analysis: analysis directive (e.g. ['.op'], ['.ac', 'dec', '10', '1', '100k'])
        :param kwargs: optional IC, source_type, control_source, plot_cmd, tf_cmd
        :return: Network instance

        Example::

            net = Network.from_parts(
                names=['R1', 'R2', 'V1'],
                values=[1000.0, 2000.0, 5.0],
                nodes=np.array([[1, 0], [2, 0], [1, 0]]),
                analysis=['.op'],
            )
            net_solve(net)
        """
        net = cls.__new__(cls)
        net._init_from_parts(names, values, nodes, analysis, **kwargs)
        net.A = None
        net.G = None
        net.C = None
        net.rhs = None
        net.isort = None
        net.t = None
        net.f = None
        net.x = None
        net.vb = None
        net.ib = None
        net.pb = None
        return net

    # ------------------------------------------------------------------
    # String representations
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return "SpicePy.Network: {} analysis".format(self.analysis[0])

    def __str__(self) -> str:
        num2node = {num: name for name, num in self.node_label2num.items()}

        msg = '------------------------\n'
        msg += '    SpicePy.Network:\n'
        msg += '------------------------\n'

        for ele, nodes, val in zip(self.names, self.nodes, self.values):
            n1 = num2node[nodes[0]]
            n2 = num2node[nodes[1]]

            if isinstance(val, list):
                if self.source_type[ele] == 'pwl':
                    fmt = "{} {} {} {}(" + "{} " * (len(val[0]) - 1) + "{})\n"
                    msg += fmt.format(ele, n1, n2, self.source_type[ele], *val[0])
                else:
                    fmt = "{} {} {} {}(" + "{} " * (len(val) - 1) + "{})\n"
                    msg += fmt.format(ele, n1, n2, self.source_type[ele], *val)
            elif ele[0].upper() in ('E', 'G'):
                msg += "{} {} {} {} {} {}\n".format(
                    ele, n1, n2,
                    self.control_source[ele][0], self.control_source[ele][1], val,
                )
            elif ele[0].upper() in ('F', 'H'):
                msg += "{} {} {} {} {}\n".format(
                    ele, n1, n2, self.control_source[ele], val,
                )
            elif np.iscomplex(val):
                msg += "{} {} {} {} {}\n".format(
                    ele, n1, n2, np.abs(val), np.angle(val) * 180 / np.pi,
                )
            elif ele[0].upper() in ('C', 'L'):
                if ele in self.IC:
                    msg += "{} {} {} {} ic={}\n".format(ele, n1, n2, val, self.IC[ele])
                else:
                    msg += "{} {} {} {}\n".format(ele, n1, n2, val)
            else:
                msg += "{} {} {} {}\n".format(ele, n1, n2, val)

        msg += " ".join(self.analysis) + '\n'

        if self.plot_cmd is not None:
            msg += self.plot_cmd + '\n'
        if self.tf_cmd is not None:
            msg += self.tf_cmd + '\n'

        msg += '------------------------\n'
        msg += '* number of nodes {}\n'.format(self.node_num + 1)
        msg += '* number of branches {}\n'.format(len(self.names))
        msg += '------------------------\n'

        return msg

    # ------------------------------------------------------------------
    # Backward-compatible aliases
    # ------------------------------------------------------------------

    def convert_unit(self, string_value: str) -> str:
        """Convert SPICE unit prefix (kept for backward compatibility)."""
        return convert_unit(string_value)

    def read_netlist(self, filename: str):
        """Parse netlist (kept for backward compatibility)."""
        data = parse_netlist(filename)
        return (
            data.names, data.values, data.IC, data.source_type,
            data.control_source, data.nodes, data.node_label2num,
            data.node_num, data.analysis, data.plot_cmd, data.tf_cmd,
        )

    # ------------------------------------------------------------------
    # Reordering
    # ------------------------------------------------------------------

    def reorder(self) -> None:
        """Sort components by type (R, L, C, V, I, E, F, G, H) and numeric suffix."""
        buckets: list[list[tuple[int, int]]] = [[] for _ in range(9)]
        letter_to_idx = {
            'R': 0, 'L': 1, 'C': 2, 'V': 3, 'I': 4,
            'E': 5, 'F': 6, 'G': 7, 'H': 8,
        }

        for k, ele in enumerate(self.names):
            idx = letter_to_idx[ele[0].upper()]
            buckets[idx].append((int(ele[1:]), k))

        self.isort = [[k for _, k in sorted(bucket)] for bucket in buckets]

    # ------------------------------------------------------------------
    # Matrix construction (delegates to mna module)
    # ------------------------------------------------------------------

    def incidence_matrix(self) -> None:
        """Build branch-to-node incidence matrix. Updates self.A."""
        self.A = build_incidence_matrix(self.nodes)

    def conductance_matrix(self) -> None:
        """Build MNA conductance matrix. Updates self.G."""
        if self.isort is None:
            self.reorder()
        self.G = build_conductance_matrix(
            self.names, self.values, self.nodes, self.node_num,
            self.isort, self.control_source, self.node_label2num,
        )

    def dynamic_matrix(self) -> None:
        """Build dynamic matrix for L and C. Updates self.C."""
        if self.isort is None:
            self.reorder()
        self.C = build_dynamic_matrix(
            self.values, self.nodes, self.node_num, self.isort, self.G.shape,
        )

    def rhs_matrix(self) -> Union[np.ndarray, callable, None]:
        """Build RHS vector (static) or closure (transient). Updates self.rhs."""
        if self.isort is None:
            self.reorder()

        if self.analysis[0] == '.tran':
            return build_rhs_transient(
                self.names, self.values, self.nodes, self.node_num,
                self.isort, self.source_type,
            )
        else:
            self.rhs = build_rhs_static(
                self.values, self.nodes, self.node_num, self.isort,
            )
            return self.rhs

    # ------------------------------------------------------------------
    # Frequency span (for .ac analysis)
    # ------------------------------------------------------------------

    def frequency_span(self) -> None:
        """Generate frequency array for .ac analysis. Updates self.f."""
        if self.analysis[0].lower() != '.ac':
            raise ValueError("frequency_span works only for .ac analyses")

        if self.analysis[1].lower() == 'lin':
            npt = int(self.analysis[2])
            fs = float(convert_unit(self.analysis[3]))
            fe = float(convert_unit(self.analysis[4]))
            self.f = np.linspace(fs, fe, npt)

        elif self.analysis[1].lower() == 'dec':
            npt_d = float(self.analysis[2])
            fs = np.log10(float(convert_unit(self.analysis[3])))
            fe = np.log10(float(convert_unit(self.analysis[4])))
            self.f = np.logspace(fs, fe, int(np.ceil(npt_d * (fe - fs)).item()))

        elif self.analysis[1].lower() == 'oct':
            npt_d = float(self.analysis[2])
            fs = np.log2(float(convert_unit(self.analysis[3])))
            fe = np.log2(float(convert_unit(self.analysis[4])))
            self.f = np.logspace(fs, fe, int(np.ceil(npt_d * (fe - fs)).item()), base=2)

        if self.f.size == 1:
            self.f = self.f.item()

    # ------------------------------------------------------------------
    # Post-solution analysis (delegates to results module)
    # ------------------------------------------------------------------

    def branch_voltage(self) -> None:
        """Compute branch voltages. Updates self.vb."""
        if self.A is None:
            self.incidence_matrix()
        if self.x is None:
            print("No solution available")
            return
        self.vb = compute_branch_voltage(self.A, self.x, self.node_num)

    def branch_current(self) -> None:
        """Compute branch currents. Updates self.ib."""
        if self.vb is None:
            self.branch_voltage()
        self.ib = compute_branch_current(
            self.names, self.values, self.nodes, self.node_num,
            self.isort, self.control_source, self.vb, self.x,
            self.analysis, self.source_type, self.f, self.t,
            self.node_label2num,
        )

    def branch_power(self) -> None:
        """Compute branch power. Updates self.pb."""
        if self.vb is None:
            self.branch_voltage()
        if self.ib is None:
            self.branch_current()
        self.pb = compute_branch_power(self.vb, self.ib, self.analysis[0])

    def get_voltage(self, arg: Union[str, list]) -> np.ndarray:
        """Compute voltage across components or between node pairs."""
        return get_voltage(
            arg, self.names, self.nodes, self.node_num,
            self.x, self.analysis, self.f, self.t, self.node_label2num,
        )

    def get_current(self, arg: Union[str, list]) -> np.ndarray:
        """Compute current through components."""
        if isinstance(arg, str):
            current_list = arg.upper().split()
        else:
            current_list = [self.names[idx] for idx in arg]

        if self.analysis[0].lower() == '.tran':
            i = np.zeros((len(current_list), self.t.size), dtype=self.x.dtype)
        elif self.analysis[0].lower() == '.ac' and not np.isscalar(self.f):
            i = np.zeros((len(current_list), self.f.size), dtype=self.x.dtype)
        else:
            i = np.zeros(len(current_list), dtype=self.x.dtype)

        for k, variable in enumerate(current_list):
            for char in ('(', ')'):
                variable = variable.replace(char, '')
            if variable not in self.names:
                variable = self.names[int(variable)]
            i[k, ...] = get_current(
                variable, self.names, self.values, self.nodes, self.node_num,
                self.isort, self.control_source, self.x, self.analysis,
                self.source_type, self.f, self.t, self.node_label2num,
            )

        if len(i.shape) == 2 and i.shape[0] == 1:
            i = i.flatten()
        return i

    # ------------------------------------------------------------------
    # Display (delegates to display module)
    # ------------------------------------------------------------------

    def print(self, variable: str = 'all', polar: bool = False, message: bool = False):
        """Print branch voltages, currents, and/or powers."""
        if self.isort is None:
            self.reorder()
        if self.vb is None:
            self.branch_voltage()
        if self.ib is None:
            self.branch_current()
        if self.pb is None:
            self.branch_power()

        return print_results(
            self.names, self.isort, self.vb, self.ib, self.pb,
            self.analysis[0], variable, polar, message,
        )

    def plot(self, to_file: bool = False, filename: str = None, dpi_value: int = 150):
        """Plot transient analysis results."""
        return plot_transient(self, to_file, filename, dpi_value)

    def bode(self, decibel: bool = False, to_file: bool = False,
             filename: str = None, dpi_value: int = 150):
        """Plot Bode diagrams for .tf transfer functions."""
        return plot_bode(self, decibel, to_file, filename, dpi_value)
