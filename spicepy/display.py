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

# ---------------------------------------------------------------------------
# Component type index labels (matches isort ordering)
# ---------------------------------------------------------------------------
_COMP_LABELS = ['R', 'L', 'C', 'V', 'I', 'E', 'F', 'G', 'H']

_POWER_UNITS_OP = {
    0: 'W', 1: 'W', 2: 'W', 3: 'W', 4: 'W',
    5: 'W', 6: 'W', 7: 'W', 8: 'W',
}
_POWER_UNITS_AC = {
    0: 'W', 1: 'var', 2: 'var', 3: 'VA', 4: 'VA',
    5: 'VA', 6: 'VA', 7: 'VA', 8: 'VA',
}


def _fmt_scalar(value, fmt_char: str, unit: str, polar: bool) -> str:
    """Format a scalar value with optional polar notation."""
    if polar:
        return f"{np.abs(value):10.4g} {unit} < {np.angle(value, deg=True):10.4g}\u00b0"
    return f"{value:10.4g} {unit}"


def _fmt_value(value, polar: bool) -> str:
    """Format a single value (scalar or array) for voltage."""
    if isinstance(value, np.ndarray):
        return f"[{value[0]:10.4g} ... {value[-1]:10.4g}] V ({len(value)} pts)"
    return _fmt_scalar(value, 'g', 'V', polar)


def _fmt_current(value, polar: bool) -> str:
    if isinstance(value, np.ndarray):
        return f"[{value[0]:10.4g} ... {value[-1]:10.4g}] A ({len(value)} pts)"
    return _fmt_scalar(value, 'g', 'A', polar)


def _fmt_power(value, unit: str, polar: bool) -> str:
    if isinstance(value, np.ndarray):
        return f"[{value[0]:10.4g} ... {value[-1]:10.4g}] {unit} ({len(value)} pts)"
    return _fmt_scalar(value, 'g', unit, polar)


def print_results(
    names: list[str],
    isort: list[list[int]],
    vb: np.ndarray,
    ib: np.ndarray,
    pb: np.ndarray,
    analysis: str,
    variable: str = 'all',
    polar: bool = False,
    message: bool = False,
) -> Union[str, None]:
    """Print branch voltages, currents, and/or powers in a formatted table.

    This replaces the original 300-line Network.print() with a single DRY loop.

    :param variable: 'voltage', 'current', 'power', or 'all'
    :param polar: if True, show magnitude and phase
    :param message: if True, return string instead of printing
    :return: string if message=True, else None
    """
    if variable.lower() == 'power' and analysis.lower() == '.tran':
        print("Function not supported for transient")
        return -1

    units = _POWER_UNITS_AC if analysis.lower() == '.ac' else _POWER_UNITS_OP

    msg = '==============================================\n'

    if variable.lower() == 'voltage':
        msg += '             branch voltages\n'
    elif variable.lower() == 'current':
        msg += '             branch currents\n'
    elif variable.lower() == 'power':
        msg += '             branch powers\n'
    else:
        msg += '               branch quantities\n'

    msg += '==============================================\n'

    for k, index in enumerate(isort):
        if not index:
            continue

        for h in index:
            if variable.lower() in ('voltage', 'all'):
                msg += f"v({names[h]}) = {_fmt_value(vb[h], polar)}\n"

            if variable.lower() in ('current', 'all'):
                msg += f"i({names[h]}) = {_fmt_current(ib[h], polar)}\n"

            if variable.lower() in ('power', 'all'):
                msg += f"p({names[h]}) = {_fmt_power(pb[h], units[k], polar)}\n"

            msg += '----------------------------------------------\n'

    if message:
        return msg
    else:
        print(msg)
        return None


def plot_transient(net, to_file: bool = False, filename: str = None, dpi_value: int = 150):
    """Plot transient analysis results based on the .plot directive.

    :param net: Network object with solved transient data
    :return: matplotlib figure
    """
    import matplotlib.pyplot as plt

    if net.analysis[0].lower() != '.tran':
        print("plot not supported for analysis: '{}'".format(net.analysis[0]))
        return -1

    plot_cmd = net.plot_cmd.upper()
    plotV = plot_cmd.find('V(')
    plotI = plot_cmd.find('I(')

    if plotV == -1 and plotI == -1:
        print("no variables provided in this command: {}".format(plot_cmd))
        return -1

    makesubplot = (plotV != -1) and (plotI != -1)
    if makesubplot:
        Ylbl = None
    elif plotV != -1:
        Ylbl = 'voltage (V)'
    else:
        Ylbl = 'current (A)'

    plot_list = plot_cmd.split()[1:]
    legend_entries = plot_cmd.split()[1:]

    if makesubplot:
        hf, axs = plt.subplots(2, 1)
    else:
        hf = plt.figure()

    for k, variable in enumerate(plot_list):
        if variable[0] == 'V':
            var_name = variable.replace('V(', '').replace(')', '')
            v = net.get_voltage(var_name)
            if makesubplot:
                plt.sca(axs[0])
            plt.plot(net.t, v, label=legend_entries[k])

        elif variable[0] == 'I':
            var_name = variable.replace('I(', '').replace(')', '')
            i = net.get_current(var_name)
            if makesubplot:
                plt.sca(axs[1])
            plt.plot(net.t, i, label=legend_entries[k])

    if makesubplot:
        plt.sca(axs[0])
        plt.ylabel('voltage (V)', fontsize=16)
        plt.grid()
        plt.legend()
        plt.tight_layout()

        plt.sca(axs[1])
        plt.xlabel('time (s)', fontsize=16)
        plt.ylabel('current (A)', fontsize=16)
        plt.grid()
        plt.legend()
        plt.tight_layout()
    else:
        plt.xlabel('time (s)', fontsize=16)
        plt.ylabel(Ylbl, fontsize=16)
        plt.grid()
        plt.legend()
        plt.tight_layout()

    if to_file:
        if filename is None:
            filename = 'transient_plot.png'
        hf.savefig(filename, dpi=dpi_value)

    return hf


def plot_bode(
    net,
    decibel: bool = False,
    to_file: bool = False,
    filename: str = None,
    dpi_value: int = 150,
):
    """Plot Bode diagrams for transfer functions defined via .tf directive.

    :param net: Network object with solved .ac multi-frequency data
    :return: list of matplotlib figures (or single figure)
    """
    import matplotlib.pyplot as plt

    if net.analysis[0].lower() != '.ac':
        raise ValueError("bode() method available only for .ac analyses")
    if np.isscalar(net.f):
        raise ValueError(
            "bode() method useful for multi-frequency analyses. "
            "Use print() for single-frequency."
        )

    tf_array = np.array(net.tf_cmd.upper().split()[1:]).reshape(-1, 2)

    hf = []
    for tf in tf_array:
        if 'V(' in tf[0]:
            out = net.get_voltage(tf[0].replace('V(', '').replace(')', ''))
        elif 'I(' in tf[0]:
            out = net.get_current(tf[0].replace('I(', '').replace(')', ''))

        if 'V(' in tf[1]:
            inp = net.get_voltage(tf[1].replace('V(', '').replace(')', ''))
        elif 'I(' in tf[1]:
            inp = net.get_current(tf[1].replace('I(', '').replace(')', ''))

        H = out / inp

        fig, axs = plt.subplots(2, 1)
        plt.sca(axs[0])
        plt.title('tf: ' + tf[0] + '/' + tf[1], fontsize=14)
        if decibel:
            plt.semilogx(net.f, 20 * np.log10(np.abs(H)))
            plt.ylabel('magnitude (dB)', fontsize=14)
        else:
            plt.semilogx(net.f, np.abs(H))
            plt.ylabel('magnitude', fontsize=14)
        plt.grid()

        plt.sca(axs[1])
        plt.semilogx(net.f, np.angle(H) * 180 / np.pi)
        plt.xlabel('frequency (Hz)', fontsize=14)
        plt.ylabel('phase (deg)', fontsize=14)
        plt.grid()
        plt.tight_layout()

        hf.append(fig)

    if to_file:
        if filename is None:
            filename = 'bode_plot.png'
        elif not filename.lower().endswith('.png'):
            filename += '.png'

        if len(hf) == 1:
            hf[0].savefig(filename, dpi=dpi_value)
        else:
            for k, fig in enumerate(hf):
                fig.savefig(filename.replace('.png', f'_{k}.png'), dpi=dpi_value)
    else:
        if len(hf) == 1:
            return hf[0]

    return hf
