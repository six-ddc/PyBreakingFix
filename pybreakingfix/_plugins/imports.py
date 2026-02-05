from __future__ import annotations

import ast
import functools
from collections.abc import Iterable

from tokenize_rt import Offset
from tokenize_rt import Token

from pybreakingfix._ast_helpers import ast_to_offset
from pybreakingfix._data import register
from pybreakingfix._data import State
from pybreakingfix._data import TokenFunc
from pybreakingfix._token_helpers import find_end
from pybreakingfix._token_helpers import has_space_before

# Breaking change: collections ABCs moved to collections.abc in 3.10
# from collections import Mapping -> ImportError in 3.10+
# collections.Mapping -> AttributeError in 3.10+
COLLECTIONS_ABC_NAMES = frozenset((
    'AsyncGenerator',
    'AsyncIterable',
    'AsyncIterator',
    'Awaitable',
    'ByteString',
    'Callable',
    'Collection',
    'Container',
    'Coroutine',
    'Generator',
    'Hashable',
    'ItemsView',
    'Iterable',
    'Iterator',
    'KeysView',
    'Mapping',
    'MappingView',
    'MutableMapping',
    'MutableSequence',
    'MutableSet',
    'Reversible',
    'Sequence',
    'Set',
    'Sized',
    'ValuesView',
))


def _fix_collections_abc_import_pure(
        i: int,
        tokens: list[Token],
) -> None:
    """Fix 'from collections import ABCs' -> 'from collections.abc import ABCs'

    Only use when ALL imported names are ABCs.
    """
    j = i
    while j < len(tokens) and tokens[j].src != 'collections':
        j += 1
    if j < len(tokens):
        tokens[j] = tokens[j]._replace(src='collections.abc')


def _fix_collections_abc_import_mixed(
        i: int,
        tokens: list[Token],
        *,
        abc_names: list[str],
        non_abc_names: list[str],
) -> None:
    """Fix mixed imports: split into two import statements.

    from collections import namedtuple, Mapping
    ->
    from collections import namedtuple
    from collections.abc import Mapping
    """
    # Find the start of this import statement
    if has_space_before(i, tokens):
        start = i - 1
    else:
        start = i

    end = find_end(tokens, i)

    # Build new import statements
    lines = []
    if non_abc_names:
        lines.append(f'from collections import {", ".join(non_abc_names)}')
    if abc_names:
        lines.append(f'from collections.abc import {", ".join(abc_names)}')

    new_code = '\n'.join(lines) + '\n'

    # Replace the entire import statement
    tokens[start:end] = [Token('CODE', new_code)]


@register(ast.ImportFrom)
def visit_ImportFrom(
        state: State,
        node: ast.ImportFrom,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    # Only handle absolute imports from 'collections'
    if node.level != 0 or node.module != 'collections':
        return

    # Separate ABC names from non-ABC names
    abc_names = []
    non_abc_names = []
    for alias in node.names:
        # Use the original name, preserving any 'as' alias
        name = alias.name
        if name in COLLECTIONS_ABC_NAMES:
            if alias.asname:
                abc_names.append(f'{name} as {alias.asname}')
            else:
                abc_names.append(name)
        else:
            if alias.asname:
                non_abc_names.append(f'{name} as {alias.asname}')
            else:
                non_abc_names.append(name)

    if not abc_names:
        # No ABCs to fix
        return

    if not non_abc_names:
        # All names are ABCs - simple replacement
        yield ast_to_offset(node), _fix_collections_abc_import_pure
    else:
        # Mixed - need to split the import
        func = functools.partial(
            _fix_collections_abc_import_mixed,
            abc_names=abc_names,
            non_abc_names=non_abc_names,
        )
        yield ast_to_offset(node), func


# Track ABCs that need to be imported (used by _main.py for post-processing)
# This is reset before each file is processed
pending_abc_imports: set[str] = set()


def _fix_collections_abc_attribute(
        i: int,
        tokens: list[Token],
        *,
        abc_name: str,
        needs_import: bool,
) -> None:
    """Replace collections.ABC with just ABC.

    Example: collections.Sized -> Sized
    The import will be added by post-processing in _main.py if needs_import=True.
    """
    # Find 'collections' token
    j = i
    while j < len(tokens) and tokens[j].src != 'collections':
        j += 1
    if j >= len(tokens):
        return

    # Find the extent: 'collections' '.' 'ABC'
    # We need to replace all three tokens with just 'ABC'
    start = j
    end = j + 1

    # Skip the dot
    while end < len(tokens) and tokens[end].src in ('', '.'):
        end += 1

    # Now end should point to the ABC name
    if end < len(tokens) and tokens[end].src == abc_name:
        end += 1
        # Replace everything from 'collections' to 'ABC' with just 'ABC'
        tokens[start:end] = [tokens[start]._replace(src=abc_name)]

    # Track that we need to import this ABC (only if not already imported)
    if needs_import:
        pending_abc_imports.add(abc_name)


@register(ast.Attribute)
def visit_Attribute(
        state: State,
        node: ast.Attribute,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    """Handle collections.Sized -> Sized (with auto import)."""
    if (
            isinstance(node.value, ast.Name) and
            node.value.id == 'collections' and
            node.attr in COLLECTIONS_ABC_NAMES
    ):
        # Check if this ABC is already imported from collections.abc
        already_imported = node.attr in state.from_imports.get('collections.abc', set())
        func = functools.partial(
            _fix_collections_abc_attribute,
            abc_name=node.attr,
            needs_import=not already_imported,
        )
        yield ast_to_offset(node), func
