# PyBreakingFix

A tool to detect and fix Python breaking changes when upgrading from 3.7 to 3.12.

## What It Does

PyBreakingFix focuses exclusively on **breaking changes** that cause runtime errors when upgrading Python versions. It does NOT handle code style optimizations.

**Breaking Change Definition**: Code that works in Python 3.7 but causes runtime errors (ImportError, AttributeError, etc.) in Python 3.12.

## Installation

```bash
pip install pybreakingfix
```

## Usage

```bash
# Fix breaking changes (3.7 -> 3.12)
pybreakingfix your_file.py

# Check only (don't modify files)
pybreakingfix --check your_file.py

# Process from stdin
echo "from collections import Mapping" | pybreakingfix -
```

### Exit Codes

- `0`: Code is compatible, no changes needed
- `1`: Changes were made (or would be made in check mode)
- `2`: Fatal errors detected (removed modules that need manual migration)

## Supported Fixes

### Deprecated Module Functions (Removed in 3.9+)

```diff
# base64 module
-base64.encodestring(data)
+base64.encodebytes(data)

-base64.decodestring(data)
+base64.decodebytes(data)
```

### Warnings for Potential Issues

For method calls where we cannot determine the object type statically, we print **yellow warnings** for manual review:

```
file.py:10: WARNING: .fromstring() - check if this is array.array, if so use .frombytes() instead (etree.fromstring() is valid, no change needed)
file.py:15: WARNING: .isAlive() - check if this is threading.Thread, if so use .is_alive() instead
```

These require manual review because we cannot statically determine object types:
- `arr.tostring()` / `arr.fromstring()` - could be `array.array` (needs fix) or `etree` (valid)
- `thread.isAlive()` - could be `threading.Thread` (needs fix) or other objects

### asyncio API Changes (Removed in 3.9+)

```diff
-asyncio.Task.current_task()
+asyncio.current_task()

-asyncio.Task.all_tasks()
+asyncio.all_tasks()
```

### fractions.gcd Migration (Removed in 3.9+)

```diff
-fractions.gcd(a, b)
+math.gcd(a, b)

-from fractions import gcd
+from math import gcd
```

### collections ABCs Migration (Removed in 3.10+)

**Import statements:**
```diff
-from collections import Mapping, Sequence
+from collections.abc import Mapping, Sequence
```

**Attribute access (auto-fixed with import):**
```diff
+from collections.abc import Sized
 import collections
-if isinstance(x, collections.Sized):
+if isinstance(x, Sized):
     pass
```

## Detected Errors (Removed Modules)

The following modules have been removed in Python 3.12 and require manual migration. PyBreakingFix will report these as errors (exit code 2):

| Removed Module | Alternative |
|----------------|-------------|
| `distutils` | Use `setuptools` |
| `asynchat` | Use `asyncio` |
| `asyncore` | Use `asyncio` |
| `smtpd` | Use `aiosmtpd` package |
| `imp` | Use `importlib` |

## Development

### Running Tests

```bash
pip install pytest
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

## License

MIT

## Credits

Forked from [pyupgrade](https://github.com/asottile/pyupgrade) by Anthony Sottile.
