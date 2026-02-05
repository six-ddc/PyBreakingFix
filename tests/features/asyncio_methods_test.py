from __future__ import annotations

import pytest

from pybreakingfix._data import Settings
from pybreakingfix._main import _fix_plugins


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        pytest.param(
            'asyncio.Task.current_task()\n',
            'asyncio.current_task()\n',
            id='Task.current_task -> current_task',
        ),
        pytest.param(
            'asyncio.Task.all_tasks()\n',
            'asyncio.all_tasks()\n',
            id='Task.all_tasks -> all_tasks',
        ),
        pytest.param(
            'task = asyncio.Task.current_task(loop)\n',
            'task = asyncio.current_task(loop)\n',
            id='Task.current_task with arg',
        ),
    ),
)
def test_asyncio_task_methods(s, expected):
    """Test asyncio.Task class methods to module-level functions."""
    settings = Settings(min_version=(3, 12))
    assert _fix_plugins(s, settings=settings) == expected


@pytest.mark.parametrize(
    ('s',),
    (
        pytest.param(
            'asyncio.Task.current_task()\n',
            id='Task.current_task not fixed for 3.8',
        ),
    ),
)
def test_asyncio_version_check(s):
    """Test that asyncio methods are not fixed for old versions."""
    settings = Settings(min_version=(3, 8))
    assert _fix_plugins(s, settings=settings) == s


def test_asyncio_regular_task_not_affected():
    """Test that regular asyncio usage is not affected."""
    s = 'task = asyncio.create_task(coro)\n'
    settings = Settings(min_version=(3, 12))
    assert _fix_plugins(s, settings=settings) == s
