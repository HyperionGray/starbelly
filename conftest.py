"""
conftest.py - Root configuration for pytest.

Provides mock modules for native dependencies that cannot be compiled in
the current test environment (e.g. cchardet requires a C extension).
This allows the test suite to run without the full production dependency
stack while still testing pure-Python logic.
"""
import sys
import types
from unittest.mock import MagicMock


def mock_module(name, **attrs):
    '''Create a stub module and register it in sys.modules.'''
    mod = types.ModuleType(name)
    for attr, value in attrs.items():
        setattr(mod, attr, value)
    sys.modules[name] = mod
    return mod


# ---------------------------------------------------------------------------
# cchardet  – C extension for character-set detection
# ---------------------------------------------------------------------------
if 'cchardet' not in sys.modules:
    mock_module('cchardet', detect=lambda s: {'encoding': 'utf-8'})

# ---------------------------------------------------------------------------
# formasaurus  – ML-based form classifier (large C/scikit-learn dependency)
# ---------------------------------------------------------------------------
if 'formasaurus' not in sys.modules:
    fm = mock_module('formasaurus')
    fm.FormAnnotator = MagicMock
    fm.utils = mock_module('formasaurus.utils')
