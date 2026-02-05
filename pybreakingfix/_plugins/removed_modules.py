"""
Plugin to detect imports of removed modules.

Note: This plugin is a placeholder for documentation purposes.
The actual error reporting for removed modules is handled in _main.py
since these require manual migration rather than automatic fixing.

Removed modules in Python 3.12:
- distutils -> use setuptools
- asynchat -> use asyncio
- asyncore -> use asyncio
- smtpd -> use aiosmtpd (external package)
- imp -> use importlib
"""
from __future__ import annotations

# Removed modules and their alternatives
REMOVED_MODULES = {
    'distutils': 'setuptools',
    'asynchat': 'asyncio',
    'asyncore': 'asyncio',
    'smtpd': 'aiosmtpd (external package)',
    'imp': 'importlib',
}

# Version when each module was removed
REMOVAL_VERSIONS = {
    'distutils': (3, 12),
    'asynchat': (3, 12),
    'asyncore': (3, 12),
    'smtpd': (3, 12),
    'imp': (3, 12),
}
