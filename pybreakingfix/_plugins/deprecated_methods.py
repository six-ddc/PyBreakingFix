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


# Module-level function renames: (module, old_func) -> new_func
# These are safe to replace because we can verify the module name
MODULE_FUNCTION_RENAMES = {
    # base64 module (removed in 3.9)
    ('base64', 'encodestring'): 'encodebytes',
    ('base64', 'decodestring'): 'decodebytes',
}

# NOTE: We intentionally do NOT auto-replace these because we cannot
# statically determine the object type:
#
# - arr.tostring() / arr.fromstring() - could be array.array or other objects
# - thread.isAlive() - could be threading.Thread or other objects
# - element.getchildren() / element.getiterator() - could be xml Element or other
# - etree.tostring() is a VALID function in xml.etree.ElementTree!
#
# These require manual review or type-aware tools.


def _fix_module_function_rename(
        i: int,
        tokens: list[Token],
        *,
        old_name: str,
        new_name: str,
) -> None:
    """Replace old function name with new function name."""
    while i < len(tokens):
        if tokens[i].src == old_name:
            tokens[i] = tokens[i]._replace(src=new_name)
            return
        i += 1


@register(ast.Call)
def visit_Call(
        state: State,
        node: ast.Call,
        parent: ast.AST,
) -> Iterable[tuple[Offset, TokenFunc]]:
    # Skip if not targeting 3.9+
    if state.settings.min_version < (3, 9):
        return

    # Handle module-level function calls: module.func()
    # Only match when we can verify the module name
    if (
            isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Name)
    ):
        module_name = node.func.value.id
        func_name = node.func.attr
        key = (module_name, func_name)

        if key in MODULE_FUNCTION_RENAMES:
            new_name = MODULE_FUNCTION_RENAMES[key]
            func = functools.partial(
                _fix_module_function_rename,
                old_name=func_name,
                new_name=new_name,
            )
            yield ast_to_offset(node), func
