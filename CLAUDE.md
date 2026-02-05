# PyBreakingFix

A tool to detect and fix Python breaking changes when upgrading from 3.7 to 3.12.

## Project Purpose

PyBreakingFix focuses exclusively on **breaking changes** that cause runtime errors when upgrading Python versions. It does NOT handle code style optimizations.

**Breaking Change Definition**: Code that works in Python 3.7 but causes runtime errors (ImportError, AttributeError, etc.) in Python 3.12.

### What We Fix (Automatic)

1. **Deprecated module functions** (removed in 3.9+)
   - `base64.encodestring()` → `base64.encodebytes()`
   - `base64.decodestring()` → `base64.decodebytes()`

   Note: We only auto-fix calls where we can verify the module name.
   For instance methods like `arr.tostring()`, we print yellow warnings
   for manual review (since we cannot determine object types statically).

2. **asyncio API changes** (removed in 3.9+)
   - `asyncio.Task.current_task()` → `asyncio.current_task()`
   - `asyncio.Task.all_tasks()` → `asyncio.all_tasks()`

3. **fractions.gcd** (removed in 3.9+)
   - `fractions.gcd()` → `math.gcd()`

4. **collections ABCs** (removed in 3.10+)
   - `from collections import Mapping` → `from collections.abc import Mapping`
   - `collections.Sized` → `Sized` (with auto `from collections.abc import Sized`)

### What We Report (Errors)

Removed modules (require manual migration, exit code 2):
- `distutils` → use `setuptools`
- `asynchat` → use `asyncio`
- `asyncore` → use `asyncio`
- `smtpd` → use `aiosmtpd`
- `imp` → use `importlib`

## Usage

```bash
# Fix breaking changes (3.7 -> 3.12)
pybreakingfix your_file.py

# Check only (don't modify files)
pybreakingfix --check your_file.py
```

### Exit Codes

- `0`: Code is compatible
- `1`: Changes made (or would be made)
- `2`: Fatal errors (removed modules)

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure

```
pybreakingfix/
├── _main.py           # CLI entry point
├── _data.py           # Settings, plugin registration
├── _plugins/          # Detection and fix plugins
│   ├── deprecated_methods.py
│   ├── asyncio_methods.py
│   ├── fractions_gcd.py
│   ├── imports.py
│   └── removed_modules.py
└── _token_helpers.py  # Token manipulation utilities
```

### Adding New Fixes

1. Create a new plugin in `pybreakingfix/_plugins/`
2. Use `@register(ast.NodeType)` decorator to register AST handlers
3. Return `(offset, callback)` tuples for fixes
4. Add tests in `tests/features/`
