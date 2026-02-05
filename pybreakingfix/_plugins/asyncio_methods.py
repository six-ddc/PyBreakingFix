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


# asyncio.Task class methods that became module-level functions in 3.9
# asyncio.Task.current_task() -> asyncio.current_task()
# asyncio.Task.all_tasks() -> asyncio.all_tasks()
ASYNCIO_TASK_METHODS = {
    'current_task': 'asyncio.current_task',
    'all_tasks': 'asyncio.all_tasks',
}


def _fix_asyncio_task_method(
        i: int,
        tokens: list[Token],
        *,
        new_call: str,
) -> None:
    """Replace asyncio.Task.method() with asyncio.method()"""
    # Find the start of 'asyncio'
    j = i
    while j < len(tokens) and tokens[j].src != 'asyncio':
        j += 1
    if j >= len(tokens):
        return

    start = j

    # Skip to end of call: asyncio.Task.method()
    # We need to find the closing paren
    depth = 0
    k = j
    while k < len(tokens):
        if tokens[k].src == '(':
            depth += 1
        elif tokens[k].src == ')':
            depth -= 1
            if depth == 0:
                break
        k += 1

    if k >= len(tokens):
        return

    end = k + 1

    # Build the new call, preserving any arguments
    # Find arguments between ( and )
    paren_start = None
    for m in range(start, end):
        if tokens[m].src == '(':
            paren_start = m
            break

    if paren_start is None:
        return

    # Extract arguments
    args_tokens = tokens[paren_start + 1:k]
    args_str = ''.join(t.src for t in args_tokens).strip()

    # Build replacement
    new_code = f'{new_call}({args_str})'
    tokens[start:end] = [Token('CODE', new_code)]


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    # Skip if not targeting 3.9+
    if state.settings.min_version < (3, 9):
        return

    # Check for asyncio.Task.current_task() or asyncio.Task.all_tasks()
    # Pattern: asyncio.Task.method()
    if (
            isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Attribute) and
            isinstance(node.func.value.value, ast.Name) and
            node.func.value.value.id == 'asyncio' and
            node.func.value.attr == 'Task' and
            node.func.attr in ASYNCIO_TASK_METHODS
    ):
        new_call = ASYNCIO_TASK_METHODS[node.func.attr]
        func = functools.partial(_fix_asyncio_task_method, new_call=new_call)
        yield ast_to_offset(node), func
