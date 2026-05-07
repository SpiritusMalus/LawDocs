"""Shared fixtures for all tests."""
from pathlib import Path

import pytest

from app.situations.registry import registry

CONFIGS_DIR = Path(__file__).parent.parent / "app" / "situations" / "configs"


@pytest.fixture(scope="session", autouse=True)
def load_registry():
    """Load the situation registry once for the entire test session."""
    registry.load(CONFIGS_DIR)
    yield
