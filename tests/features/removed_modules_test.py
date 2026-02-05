from __future__ import annotations

import pytest

from pybreakingfix._main import _check_removed_modules


@pytest.mark.parametrize(
    ('s', 'expected_module'),
    (
        pytest.param(
            'import distutils\n',
            'distutils',
            id='import distutils',
        ),
        pytest.param(
            'from distutils import core\n',
            'distutils',
            id='from distutils import',
        ),
        pytest.param(
            'import asynchat\n',
            'asynchat',
            id='import asynchat',
        ),
        pytest.param(
            'import asyncore\n',
            'asyncore',
            id='import asyncore',
        ),
        pytest.param(
            'import smtpd\n',
            'smtpd',
            id='import smtpd',
        ),
        pytest.param(
            'import imp\n',
            'imp',
            id='import imp',
        ),
    ),
)
def test_removed_modules_detected(s, expected_module):
    """Test that removed modules are detected."""
    errors = _check_removed_modules(s)
    assert len(errors) == 1
    assert errors[0][1] == expected_module


def test_removed_modules_not_detected():
    """Test that valid modules are not flagged."""
    s = 'import os\nimport sys\n'
    errors = _check_removed_modules(s)
    assert len(errors) == 0


def test_removed_modules_multiple():
    """Test detection of multiple removed modules."""
    s = 'import distutils\nimport asyncore\n'
    errors = _check_removed_modules(s)
    assert len(errors) == 2


def test_removed_modules_suggestion():
    """Test that suggestions are provided."""
    s = 'import distutils\n'
    errors = _check_removed_modules(s)
    assert 'setuptools' in errors[0][2].lower()
