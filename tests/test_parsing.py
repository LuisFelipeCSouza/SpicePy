"""Tests for spicepy.parsing module."""

import os

import pytest

from spicepy.parsing import convert_unit, parse_netlist

DEMO_DIR = os.path.join(os.path.dirname(__file__), '..', 'demo')


class TestConvertUnit:
    def test_kilo(self):
        assert convert_unit('10k') == '10e3'

    def test_mega(self):
        assert convert_unit('1meg') == '1e6'

    def test_milli(self):
        assert convert_unit('5m') == '5e-3'

    def test_micro(self):
        assert convert_unit('100u') == '100e-6'

    def test_no_prefix(self):
        assert convert_unit('100') == '100'

    def test_pico(self):
        assert convert_unit('10p') == '10e-12'

    def test_nano(self):
        assert convert_unit('100n') == '100e-9'


class TestParseNetlist:
    def test_op_network(self):
        data = parse_netlist(os.path.join(DEMO_DIR, 'op_network.net'))
        assert data.analysis == ['.op']
        assert len(data.names) > 0
        assert 0 in data.node_label2num.values()

    def test_dc_network(self):
        data = parse_netlist(os.path.join(DEMO_DIR, 'dc_network.net'))
        assert data.analysis == ['.op']
        assert len(data.names) == 6

    def test_ac_single_frequency(self):
        data = parse_netlist(os.path.join(DEMO_DIR, 'ac_single_frequency.net'))
        assert data.analysis[0] == '.ac'

    def test_tran_network1(self):
        data = parse_netlist(os.path.join(DEMO_DIR, 'tran_network1.net'))
        assert data.analysis[0] == '.tran'
        assert len(data.IC) > 0

    def test_no_analysis_raises(self):
        """Netlist without analysis directive should raise ValueError."""
        import tempfile
        path = os.path.join(tempfile.gettempdir(), 'spicepy_test_no_analysis.net')
        with open(path, 'w') as f:
            f.write("R1 1 2 1k\n.end\n")
        try:
            with pytest.raises(ValueError, match="No analysis directive"):
                parse_netlist(path)
        finally:
            os.unlink(path)

    def test_controlled_sources(self):
        data = parse_netlist(os.path.join(DEMO_DIR, 'VCVS_and_CCCS.net'))
        assert len(data.control_source) > 0
