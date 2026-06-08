"""Pytest configuration."""

import pytest


@pytest.fixture
def sample_pdf():
    """Fixture para PDF de teste."""
    from pathlib import Path
    return Path("tests/fixtures/exemplo.pdf")
