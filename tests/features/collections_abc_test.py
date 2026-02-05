from __future__ import annotations

import pytest

from pybreakingfix._data import Settings
from pybreakingfix._main import _fix_plugins


def test_collections_abc_noop():
    """Test that non-ABC collections imports are not changed."""
    src = 'from collections import namedtuple, OrderedDict\n'
    assert _fix_plugins(src, settings=Settings()) == src


def test_collections_abc_noop_attribute():
    """Test that non-ABC attribute access is not changed."""
    src = 'if isinstance(x, collections.defaultdict): pass\n'
    assert _fix_plugins(src, settings=Settings()) == src


@pytest.mark.parametrize(
    ('src', 'expected'),
    (
        pytest.param(
            'from collections import Mapping\n',
            'from collections.abc import Mapping\n',
            id='pure ABC import',
        ),
        pytest.param(
            'from collections import Mapping, Sequence\n',
            'from collections.abc import Mapping, Sequence\n',
            id='multiple pure ABC imports',
        ),
        pytest.param(
            'from collections import namedtuple, Mapping\n',
            'from collections import namedtuple\n'
            'from collections.abc import Mapping\n',
            id='mixed import - split into two',
        ),
        pytest.param(
            'from collections import namedtuple, OrderedDict, Iterable\n',
            'from collections import namedtuple, OrderedDict\n'
            'from collections.abc import Iterable\n',
            id='mixed import with multiple non-ABCs',
        ),
    ),
)
def test_collections_abc_rewrite(src, expected):
    assert _fix_plugins(src, settings=Settings()) == expected


def test_collections_abc_attribute_auto_fixed():
    """Test that collections.ABC attribute access is auto-fixed.

    collections.Sized -> Sized with auto import
    """
    src = 'if isinstance(x, collections.Sized):\n    print(len(x))\n'
    expected = (
        'from collections.abc import Sized\n'
        'if isinstance(x, Sized):\n'
        '    print(len(x))\n'
    )
    assert _fix_plugins(src, settings=Settings()) == expected


def test_collections_abc_multiple_attributes():
    """Test multiple different ABC attribute accesses."""
    src = (
        'if isinstance(x, collections.Sized):\n'
        '    pass\n'
        'if isinstance(y, collections.Mapping):\n'
        '    pass\n'
    )
    expected = (
        'from collections.abc import Mapping, Sized\n'
        'if isinstance(x, Sized):\n'
        '    pass\n'
        'if isinstance(y, Mapping):\n'
        '    pass\n'
    )
    assert _fix_plugins(src, settings=Settings()) == expected


def test_collections_abc_already_imported():
    """Test that we don't add duplicate imports."""
    src = (
        'from collections.abc import Sized\n'
        'if isinstance(x, collections.Sized):\n'
        '    pass\n'
    )
    expected = (
        'from collections.abc import Sized\n'
        'if isinstance(x, Sized):\n'
        '    pass\n'
    )
    assert _fix_plugins(src, settings=Settings()) == expected
