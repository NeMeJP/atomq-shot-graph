"""Heterogeneous backends: NI-DAQ, AD9910 DDS, camera/SLM mocks, optical delay stub.

All concrete backends subclass ``Backend`` from ``base.py``.
"""
from yaqumo_shot_graph.backends.ad9910 import AD9910Backend
from yaqumo_shot_graph.backends.base import Backend, BackendCommand, BackendRegistry
from yaqumo_shot_graph.backends.camera_mock import EMCCDCameraBackend
from yaqumo_shot_graph.backends.nidaqmx_adapter import NIDAQBackend
from yaqumo_shot_graph.backends.optical_delay import OpticalDelayBackend
from yaqumo_shot_graph.backends.slm_mock import SLMBackend

__all__ = [
    "Backend",
    "BackendCommand",
    "BackendRegistry",
    "AD9910Backend",
    "EMCCDCameraBackend",
    "NIDAQBackend",
    "OpticalDelayBackend",
    "SLMBackend",
]
