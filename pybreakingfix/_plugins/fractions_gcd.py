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


def _fix_fractions_gcd(
        i: int,
        tokens: list[Token],
        *,
        has_math_import: bool,
) -> None:
    """Replace fractions.gcd(...) with math.gcd(...)"""
    # Find 'fractions'
    j = i
    while j < len(tokens) and tokens[j].src != 'fractions':
        j += 1
    if j >= len(tokens):
        return

    # Replace 'fractions' with 'math'
    tokens[j] = tokens[j]._replace(src='math')

    # If we don't have math import, we need to add it
    # This is handled separately after the token replacement


def _fix_gcd_from_import(
        i: int,
        tokens: list[Token],
        *,
        has_math_import: bool,
) -> None:
    """Replace 'from fractions import gcd' with 'from math import gcd'"""
    # Find 'fractions' and replace with 'math'
    j = i
    while j < len(tokens) and tokens[j].src != 'fractions':
        j += 1
    if j >= len(tokens):
        return

    tokens[j] = tokens[j]._replace(src='math')


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    # Skip if not targeting 3.9+ (fractions.gcd removed in 3.9)
    if state.settings.min_version < (3, 9):
        return

    # Check for fractions.gcd(...) call
    if (
            isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'fractions' and
            node.func.attr == 'gcd'
    ):
        has_math_import = 'gcd' in state.from_imports.get('math', set())
        func = functools.partial(
            _fix_fractions_gcd,
            has_math_import=has_math_import,
        )
        yield ast_to_offset(node), func

    # Check for gcd(...) call when imported from fractions
    elif (
            isinstance(node.func, ast.Name) and
            node.func.id == 'gcd' and
            'gcd' in state.from_imports.get('fractions', set())
    ):
        # This case is handled by the import rewriting
        # The function call itself doesn't need to change
        pass


@register(ast.ImportFrom)
def visit_ImportFrom(
        state: State,
        node: ast.ImportFrom,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    # Skip if not targeting 3.9+
    if state.settings.min_version < (3, 9):
        return

    # Check for 'from fractions import gcd'
    if (
            node.module == 'fractions' and
            any(alias.name == 'gcd' for alias in node.names)
    ):
        has_math_import = 'gcd' in state.from_imports.get('math', set())
        func = functools.partial(
            _fix_gcd_from_import,
            has_math_import=has_math_import,
        )
        yield ast_to_offset(node), func
