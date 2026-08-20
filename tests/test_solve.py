"""Integration tests for the full solve pipeline."""

import os

import numpy as np

from spicepy.netlist import Network
from spicepy.netsolve import net_solve

DEMO_DIR = os.path.join(os.path.dirname(__file__), '..', 'demo')


class TestOPSolve:
    def test_op_network(self):
        net = Network(os.path.join(DEMO_DIR, 'op_network.net'))
        net_solve(net)
        assert net.x is not None
        net.branch_voltage()
        net.branch_current()
        net.branch_power()
        assert net.vb is not None
        assert net.ib is not None
        assert net.pb is not None

    def test_dc_network(self):
        net = Network(os.path.join(DEMO_DIR, 'dc_network.net'))
        net_solve(net)
        assert net.x is not None


class TestACSolve:
    def test_single_frequency(self):
        net = Network(os.path.join(DEMO_DIR, 'ac_single_frequency.net'))
        net_solve(net)
        assert net.x is not None
        assert np.iscomplexobj(net.x)

    def test_multi_frequency(self):
        net = Network(os.path.join(DEMO_DIR, 'ac_low_high_pass_filter.net'))
        net_solve(net)
        assert net.x is not None
        assert net.x.ndim == 2


class TestTranSolve:
    def test_tran_network1(self):
        net = Network(os.path.join(DEMO_DIR, 'tran_network1.net'))
        net_solve(net)
        assert net.x is not None
        assert net.t is not None

    def test_tran_network3(self):
        net = Network(os.path.join(DEMO_DIR, 'tran_network3.net'))
        net_solve(net)
        assert net.x is not None


class TestDependentSources:
    def test_vcvs_cccs(self):
        net = Network(os.path.join(DEMO_DIR, 'VCVS_and_CCCS.net'))
        net_solve(net)
        net.branch_voltage()
        net.branch_current()
        net.branch_power()
        assert net.vb is not None

    def test_vccs_ccvs(self):
        net = Network(os.path.join(DEMO_DIR, 'VCCS_and_CCVS.net'))
        net_solve(net)
        net.branch_voltage()
        net.branch_current()
        net.branch_power()
        assert net.vb is not None


class TestPrint:
    def test_print_message(self):
        net = Network(os.path.join(DEMO_DIR, 'op_network.net'))
        net_solve(net)
        result = net.print(message=True)
        assert isinstance(result, str)
        assert 'v(' in result
        assert 'i(' in result
