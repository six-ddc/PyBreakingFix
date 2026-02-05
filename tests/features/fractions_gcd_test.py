from __future__ import annotations

import pytest

from pybreakingfix._data import Settings
from pybreakingfix._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'fractions.gcd(a, b)\n',
            'math.gcd(a, b)\n',
            id='fractions.gcd -> math.gcd',
        ),
        pytest.param(
            'result = fractions.gcd(12, 8)\n',
            'result = math.gcd(12, 8)\n',
            id='fractions.gcd in assignment',
        ),
    ),
)
def test_fractions_gcd_call(s, expected):
    """Test fractions.gcd() to math.gcd() replacement."""
    settings = Settings(min_version=(3, 12))
    assert _fix_plugins(s, settings=settings) == expected


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'from fractions import gcd\n',
            'from math import gcd\n',
            id='from fractions import gcd',
        ),
    ),
)
def test_fractions_gcd_import(s, expected):
    """Test from fractions import gcd replacement."""
    settings = Settings(min_version=(3, 12))
    assert _fix_plugins(s, settings=settings) == expected


@pytest.mark.parametrize(
    ('s',),
    (
        pytest.param(
            'fractions.gcd(a, b)\n',
            id='fractions.gcd not fixed for 3.8',
        ),
    ),
)
def test_fractions_gcd_version_check(s):
    """Test that fractions.gcd is not fixed for old versions."""
    settings = Settings(min_version=(3, 8))
    assert _fix_plugins(s, settings=settings) == s


def test_fractions_other_not_affected():
    """Test that other fractions functions are not affected."""
    s = 'fractions.Fraction(1, 2)\n'
    settings = Settings(min_version=(3, 12))
    assert _fix_plugins(s, settings=settings) == s
