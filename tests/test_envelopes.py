"""Tests for adapted QICK envelope primitives."""
from __future__ import annotations

import numpy as np
import pytest

from yaqumo_shot_graph.ir.envelopes import cosine, drag, gauss, triang


def test_cosine_shape_and_range() -> None:
    env = cosine(length=200, maxv=1.0)
    assert env.shape == (200,)
    assert env[0] == pytest.approx(0.0)
    assert env[-1] == pytest.approx(0.0, abs=1e-12)
    assert env.max() == pytest.approx(1.0, abs=1e-3)  # linspace granularity


def test_gauss_peak_and_symmetry() -> None:
    env = gauss(mu=50, si=10, length=100, maxv=1.0)
    assert env.shape == (100,)
    assert env[50] == pytest.approx(1.0)  # peak at mu
    # Symmetric around mu=50
    assert env[40] == pytest.approx(env[60], rel=1e-6)


def test_triang_peaks_at_center() -> None:
    env = triang(length=101, maxv=1.0)
    assert env.shape == (101,)
    assert env.max() == pytest.approx(1.0)
    # Peak is near the middle
    assert np.argmax(env) == 50


def test_drag_returns_two_arrays() -> None:
    i, q = drag(mu=50, si=10, length=100, maxv=1.0, delta=0.1, alpha=0.5, det=0.0)
    assert i.shape == (100,)
    assert q.shape == (100,)


def test_drag_q_is_derivative_like() -> None:
    """Q-channel should be odd around mu (derivative of Gaussian — sign changes at peak)."""
    i, q = drag(mu=50, si=10, length=100, maxv=1.0, delta=0.1, alpha=0.5, det=0.0)
    assert np.sign(q[40]) != np.sign(q[60])


def test_drag_with_zero_alpha_matches_gauss_in_I() -> None:
    """alpha=0 → qpulse=0 → I channel is the Gaussian."""
    i, q = drag(mu=50, si=10, length=100, maxv=1.0, delta=0.1, alpha=0.0, det=0.0)
    g = gauss(mu=50, si=10, length=100, maxv=1.0)
    np.testing.assert_allclose(i, g, rtol=1e-6)
    np.testing.assert_allclose(q, np.zeros_like(q), atol=1e-12)
