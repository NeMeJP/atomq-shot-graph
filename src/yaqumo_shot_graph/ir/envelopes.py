"""Pulse envelope generator library.

Adapted verbatim from QICK (MIT License, Copyright (c) Open Quantum Hardware):
https://github.com/openquantumhardware/qick/blob/main/qick_lib/qick/helpers.py

Attribution: the four envelope functions below are lifted unchanged from
QICK's ``helpers.py``. See THIRD_PARTY_NOTICES.md for the full MIT license
text and REFERENCES.md for why these specific primitives were chosen.

The DRAG implementation is cross-referenced against QubiC and Qiskit-Pulse
(see upstream comments); it follows PRL 116, 020501 (2016).
"""
# ruff: noqa: E741
from __future__ import annotations

import numpy as np
import numpy.typing as npt


def cosine(length: int = 100, maxv: float = 30000) -> npt.NDArray[np.float64]:
    """Create a numpy array containing a cosine-shaped envelope.

    Adapted from QICK helpers.py (MIT) — unchanged.
    """
    x = np.linspace(0, 2 * np.pi, length)
    y = maxv * (1 - np.cos(x)) / 2
    return np.asarray(y, dtype=np.float64)


def gauss(
    mu: float = 0, si: float = 25, length: int = 100, maxv: float = 30000,
) -> npt.NDArray[np.float64]:
    """Create a numpy array containing a Gaussian envelope.

    Adapted from QICK helpers.py (MIT) — unchanged.
    """
    x = np.arange(0, length)
    y = maxv * np.exp(-((x - mu) ** 2) / (2 * si ** 2))
    return np.asarray(y, dtype=np.float64)


def drag(
    mu: float,
    si: float,
    length: int,
    maxv: float,
    delta: float,
    alpha: float,
    det: float,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Create I and Q arrays for a DRAG pulse.

    Adapted from QICK helpers.py (MIT). Follows PRL 116, 020501 (2016); the
    upstream implementation cites QubiC and Qiskit-Pulse cross-references.
    """
    x = np.arange(0, length)
    gaus = maxv * np.exp(-((x - mu) ** 2) / (2 * si ** 2))
    dgaus = -(x - mu) / (si ** 2) * gaus

    ipulse = gaus
    qpulse = -1 * alpha * dgaus / (2 * np.pi * (delta - det))

    idet = np.cos(2 * np.pi * det * x)
    qdet = np.sin(2 * np.pi * det * x)
    idata = ipulse * idet - qpulse * qdet
    qdata = qpulse * idet + ipulse * qdet
    return idata, qdata


def triang(length: int = 100, maxv: float = 30000) -> npt.NDArray[np.float64]:
    """Create a numpy array containing a triangular envelope.

    Adapted from QICK helpers.py (MIT) — unchanged.
    """
    y = np.zeros(length)
    halflength = (length + 1) // 2
    y1 = np.linspace(0, maxv, halflength)
    y[:halflength] = y1
    y[length // 2: length] = np.flip(y1)
    return y


__all__ = ["cosine", "gauss", "drag", "triang"]
