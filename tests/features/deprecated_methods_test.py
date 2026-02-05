from __future__ import annotations

import pytest

from pybreakingfix._data import Settings
from pybreakingfix._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'base64.encodestring(data)\n',
            'base64.encodebytes(data)\n',
            id='base64 encodestring -> encodebytes',
        ),
        pytest.param(
            'base64.decodestring(data)\n',
            'base64.decodebytes(data)\n',
            id='base64 decodestring -> decodebytes',
        ),
    ),
)
def test_deprecated_module_functions(s, expected):
    """Test module-level function renames where we can verify the module."""
    settings = Settings(min_version=(3, 12))
    assert _fix_plugins(s, settings=settings) == expected


@pytest.mark.parametrize(
    ('s',),
    (
        pytest.param(
            'base64.encodestring(data)\n',
            id='base64.encodestring not fixed for 3.8',
        ),
    ),
)
def test_deprecated_methods_version_check(s):
    """Test that deprecated methods are not fixed for old versions."""
    settings = Settings(min_version=(3, 8))
    assert _fix_plugins(s, settings=settings) == s


def test_etree_tostring_not_changed():
    """Test that etree.tostring() is NOT changed (it's a valid function)."""
    s = 'etree.tostring(root, encoding="utf8")\n'
    settings = Settings(min_version=(3, 12))
    assert _fix_plugins(s, settings=settings) == s


def test_arbitrary_tostring_not_changed():
    """Test that arbitrary .tostring() calls are NOT changed.

    We cannot statically determine object types, so we don't auto-replace
    methods like tostring(), fromstring(), isAlive(), getchildren(), etc.
    """
    cases = [
        'arr.tostring()\n',
        'arr.fromstring(data)\n',
        'thread.isAlive()\n',
        'element.getchildren()\n',
        'element.getiterator()\n',
    ]
    settings = Settings(min_version=(3, 12))
    for s in cases:
        assert _fix_plugins(s, settings=settings) == s
