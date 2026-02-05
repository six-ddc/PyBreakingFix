from __future__ import annotations

import argparse
import ast
import sys
import tokenize
from collections.abc import Sequence

from tokenize_rt import reversed_enumerate
from tokenize_rt import src_to_tokens
from tokenize_rt import Token
from tokenize_rt import tokens_to_src
from tokenize_rt import UNIMPORTANT_WS

from pybreakingfix._ast_helpers import ast_parse
from pybreakingfix._data import FUNCS
from pybreakingfix._data import Settings
from pybreakingfix._data import visit
from pybreakingfix._plugins import imports as imports_plugin

# Exit codes
EXIT_OK = 0
EXIT_CHANGES = 1
EXIT_FATAL = 2

# ANSI color codes
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

# Removed modules that require manual migration
REMOVED_MODULES = {
    'distutils': 'Use setuptools instead',
    'asynchat': 'Use asyncio instead',
    'asyncore': 'Use asyncio instead',
    'smtpd': 'Use aiosmtpd package instead',
    'imp': 'Use importlib instead',
}

# Potentially deprecated methods that we cannot auto-fix
# because we cannot determine object types statically
# Format: method_name -> (deprecated_type, replacement, safe_type)
# - deprecated_type: the type where this method is deprecated
# - replacement: what to use instead
# - safe_type: type where this method is still valid (optional)
POTENTIAL_DEPRECATED_METHODS = {
    'tostring': ('array.array', '.tobytes()', 'etree'),
    'fromstring': ('array.array', '.frombytes()', 'etree'),
    'isAlive': ('threading.Thread', '.is_alive()', ''),
    'getchildren': ('xml.etree.Element', 'list(element)', ''),
    'getiterator': ('xml.etree.Element', 'element.iter()', ''),
}


def _fixup_dedent_tokens(tokens: list[Token]) -> None:
    """For whatever reason the DEDENT / UNIMPORTANT_WS tokens are misordered

    | if True:
    |     if True:
    |         pass
    |     else:
    |^    ^- DEDENT
    |+----UNIMPORTANT_WS
    """
    for i, token in enumerate(tokens):
        if token.name == UNIMPORTANT_WS and tokens[i + 1].name == 'DEDENT':
            tokens[i], tokens[i + 1] = tokens[i + 1], tokens[i]


def _fix_plugins(contents_text: str, settings: Settings) -> str:
    # Clear pending ABC imports from previous file
    imports_plugin.pending_abc_imports.clear()

    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    callbacks = visit(FUNCS, ast_obj, settings)

    if not callbacks:
        return contents_text

    try:
        tokens = src_to_tokens(contents_text)
    except tokenize.TokenError:  # pragma: no cover (bpo-2180)
        return contents_text

    _fixup_dedent_tokens(tokens)

    for i, token in reversed_enumerate(tokens):
        if not token.src:
            continue
        # though this is a defaultdict, by using `.get()` this function's
        # self time is almost 50% faster
        for callback in callbacks.get(token.offset, ()):
            callback(i, tokens)

    result = tokens_to_src(tokens).lstrip()

    # Add imports for collections.abc ABCs if needed
    if imports_plugin.pending_abc_imports:
        abc_names = sorted(imports_plugin.pending_abc_imports)
        import_line = f'from collections.abc import {", ".join(abc_names)}\n'
        # Insert at the beginning (after any existing imports will be handled by lstrip)
        result = import_line + result

    return result


def _check_removed_modules(contents_text: str) -> list[tuple[int, str, str]]:
    """Check for imports of removed modules.

    Returns list of (line_number, module_name, suggestion).
    """
    errors = []
    try:
        tree = ast_parse(contents_text)
    except SyntaxError:
        return errors

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_name = alias.name.split('.')[0]
                if mod_name in REMOVED_MODULES:
                    errors.append((
                        node.lineno,
                        mod_name,
                        REMOVED_MODULES[mod_name],
                    ))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_name = node.module.split('.')[0]
                if mod_name in REMOVED_MODULES:
                    errors.append((
                        node.lineno,
                        mod_name,
                        REMOVED_MODULES[mod_name],
                    ))

    return errors


def _check_potential_deprecated_methods(
        contents_text: str,
) -> list[tuple[int, str, str, str, str]]:
    """Check for potentially deprecated method calls.

    Returns list of (line_number, method_name, deprecated_type, replacement, safe_type).
    These are methods we cannot auto-fix because we cannot determine
    object types statically.
    """
    warnings = []
    try:
        tree = ast_parse(contents_text)
    except SyntaxError:
        return warnings

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                if method_name in POTENTIAL_DEPRECATED_METHODS:
                    # Skip if it's a known safe module call (e.g., etree.tostring)
                    if isinstance(node.func.value, ast.Name):
                        caller = node.func.value.id
                        # etree.tostring, etree.fromstring are valid
                        if caller in ('etree', 'ET', 'ElementTree'):
                            if method_name in ('tostring', 'fromstring'):
                                continue

                    deprecated_type, replacement, safe_type = POTENTIAL_DEPRECATED_METHODS[method_name]
                    warnings.append((
                        node.lineno,
                        method_name,
                        deprecated_type,
                        replacement,
                        safe_type,
                    ))

    return warnings


def _fix_file(filename: str, args: argparse.Namespace) -> int:
    if filename == '-':
        contents_bytes = sys.stdin.buffer.read()
    else:
        with open(filename, 'rb') as fb:
            contents_bytes = fb.read()

    try:
        contents_text_orig = contents_text = contents_bytes.decode()
    except UnicodeDecodeError:
        print(f'{filename} is non-utf-8 (not supported)')
        return EXIT_CHANGES

    # Check for removed modules first
    removed_errors = _check_removed_modules(contents_text)
    if removed_errors:
        for lineno, mod_name, suggestion in removed_errors:
            print(
                f'{RED}{filename}:{lineno}: '
                f'ERROR: module "{mod_name}" has been removed. {suggestion}{RESET}',
                file=sys.stderr,
            )
        return EXIT_FATAL

    # Check for potential deprecated methods and warn
    if filename != '-':  # Don't warn for stdin
        potential_warnings = _check_potential_deprecated_methods(contents_text)
        for lineno, method_name, deprecated_type, replacement, safe_type in potential_warnings:
            msg = (
                f'{YELLOW}{filename}:{lineno}: '
                f'WARNING: .{method_name}() - check if this is {deprecated_type}, '
                f'if so use {replacement} instead'
            )
            if safe_type:
                msg += f' ({safe_type}.{method_name}() is valid, no change needed)'
            msg += f'{RESET}'
            print(msg, file=sys.stderr)

    contents_text = _fix_plugins(
        contents_text,
        settings=Settings(
            min_version=args.min_version,
            check_only=args.check,
        ),
    )

    if args.check:
        if contents_text != contents_text_orig:
            print(f'{filename}: would be rewritten')
            return EXIT_CHANGES
        return EXIT_OK

    if filename == '-':
        print(contents_text, end='')
    elif contents_text != contents_text_orig:
        print(f'Rewriting {filename}', file=sys.stderr)
        with open(filename, 'w', encoding='UTF-8', newline='') as f:
            f.write(contents_text)

    return EXIT_CHANGES if contents_text != contents_text_orig else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Detect and fix Python breaking changes (3.7 -> 3.12)',
    )
    parser.add_argument('filenames', nargs='*')
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check only, do not modify files',
    )
    args = parser.parse_args(argv)

    # Fixed target version: 3.12
    args.min_version = (3, 12)

    ret = EXIT_OK
    for filename in args.filenames:
        result = _fix_file(filename, args)
        # Fatal errors take precedence
        if result == EXIT_FATAL:
            ret = EXIT_FATAL
        elif result == EXIT_CHANGES and ret != EXIT_FATAL:
            ret = EXIT_CHANGES
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
