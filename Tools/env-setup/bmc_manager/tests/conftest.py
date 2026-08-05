"""Pytest configuration and shared fixtures."""

import os

import pytest


@pytest.fixture(autouse=True)
def preserve_bmc_env(monkeypatch):
    """Preserve BMC_* env so tests that change them don't leak."""
    saved = {k: os.environ.get(k) for k in os.environ if k.startswith("BMC_")}
    yield
    for k in list(os.environ):
        if k.startswith("BMC_"):
            del os.environ[k]
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
