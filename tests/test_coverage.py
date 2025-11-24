# tests/test_coverage.py
from __future__ import annotations

import pytest


def test_pytest_cov_plugin_loaded(pytestconfig: pytest.Config) -> None:
    plugin_manager = pytestconfig.pluginmanager
    assert plugin_manager.hasplugin("cov") or plugin_manager.hasplugin("pytest_cov")
