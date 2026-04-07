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
    def _mock_extract_forms(html, proba=False):
        """Lightweight stub that uses lxml to find forms and returns
        deterministic classifications for testing purposes."""
        from lxml.html import fromstring, tostring
        doc = fromstring(html)
        results = []
        for form in doc.forms:
            fields_meta = {}
            for inp in form.inputs:
                name = inp.name
                if name is None:
                    continue
                input_type = inp.get('type', 'text')
                if input_type == 'password':
                    fields_meta[name] = {'password': 1.0}
                elif input_type == 'submit':
                    fields_meta[name] = {'submit': 1.0}
                elif 'captcha' in name.lower():
                    fields_meta[name] = {'captcha': 1.0}
                else:
                    fields_meta[name] = {'username': 1.0}
            meta = {
                'form': {'login': 1.0},
                'fields': fields_meta,
            }
            results.append((form, meta))
        return results

    fm = mock_module('formasaurus')
    fm.FormAnnotator = MagicMock
    fm.extract_forms = _mock_extract_forms
    fm.utils = mock_module('formasaurus.utils')
