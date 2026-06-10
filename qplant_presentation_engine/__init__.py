"""Compatibility package for running `python -m qplant_presentation_engine`."""

from importlib import import_module

_IMPL_MODULE = "src.qplant_presentation_engine"


def __getattr__(name: str):
    return getattr(import_module(_IMPL_MODULE), name)


def __dir__():
    return dir(import_module(_IMPL_MODULE))
