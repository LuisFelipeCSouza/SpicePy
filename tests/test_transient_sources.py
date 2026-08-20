"""Tests for spicepy.transient_sources module."""

import numpy as np
import pytest

from spicepy.transient_sources import exp, pulse, pwl, sin


class TestPWL:
    def test_simple(self):
        pairs = [[0, 0], [1, 10], [2, 0]]
        t = np.array([0, 0.5, 1.0, 1.5, 2.0])
        result = pwl(pairs, t)
        np.testing.assert_allclose(result, [0, 5, 10, 5, 0])

    def test_scalar_output(self):
        pairs = [[0, 0], [1, 10]]
        result = pwl(pairs, 0.5)
        assert result == pytest.approx(5.0)

    def test_extrapolation(self):
        pairs = [[0, 0], [1, 10]]
        t = np.array([-1, 0, 0.5, 1, 2])
        result = pwl(pairs, t)
        np.testing.assert_allclose(result, [0, 0, 5, 10, 10])


class TestPulse:
    def test_basic(self):
        t = np.linspace(0, 10, 1000)
        result = pulse(0, 5, Td=1, Tr=0.1, Tf=0.1, Pw=2, Period=5, t=t)
        assert result.size == 1000
        assert result[0] == pytest.approx(0)
        # Pulse should reach V2=5 during the high phase
        assert np.max(result) == pytest.approx(5)

    def test_scalar(self):
        t_arr = np.linspace(0, 10, 1000)
        # At t=0.5, pulse should be 0 (before Td=1)
        result_before = pulse(0, 5, Td=1, Tr=0.1, Tf=0.1, Pw=2, Period=5, t=t_arr)
        assert result_before[0] == pytest.approx(0)


class TestSin:
    def test_basic(self):
        t = np.linspace(0, 1, 1000)
        result = sin(0, 1, Freq=10, t=t)
        assert result.size == 1000
        assert result[0] == pytest.approx(0, abs=0.01)

    def test_damped(self):
        t = np.linspace(0, 1, 1000)
        result = sin(0, 1, Freq=10, Df=5, t=t)
        assert result[0] < result[100]


class TestExp:
    def test_basic(self):
        t = np.linspace(0, 5, 1000)
        result = exp(0, 10, Td1=0, tau1=1, Td2=3, tau2=1, t=t)
        assert result.size == 1000
        assert result[0] == pytest.approx(0)
