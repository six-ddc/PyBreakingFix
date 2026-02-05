from __future__ import annotations

import io
import sys
from unittest import mock

import pytest

from pybreakingfix._main import main


def test_main_trivial():
    assert main(()) == 0


def test_main_help(capsys):
    with pytest.raises(SystemExit):
        main(('--help',))
    out, err = capsys.readouterr()
    assert '--check' in out
    assert '3.7 -> 3.12' in out


def test_main_noop(tmpdir):
    s = '''\
from sys import version_info
x = version_info
def f():
    global x, y
'''
    f = tmpdir.join('f.py')
    f.write(s)

    assert main((f.strpath,)) == 0
    assert f.read() == s


def test_main_changes_a_file(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write('from collections import Mapping\n')
    assert main((f.strpath,)) == 1
    out, err = capsys.readouterr()
    assert err == f'Rewriting {f.strpath}\n'
    assert f.read() == 'from collections.abc import Mapping\n'


def test_main_keeps_line_endings(tmpdir):
    f = tmpdir.join('f.py')
    f.write_binary(b'from collections import Mapping\r\n')
    assert main((f.strpath,)) == 1
    assert f.read_binary() == b'from collections.abc import Mapping\r\n'


def test_main_syntax_error(tmpdir):
    f = tmpdir.join('f.py')
    f.write('from __future__ import print_function\nprint 1\n')
    assert main((f.strpath,)) == 0


def test_main_non_utf8_bytes(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write_binary('# -*- coding: cp1252 -*-\nx = €\n'.encode('cp1252'))
    assert main((f.strpath,)) == 1
    out, _ = capsys.readouterr()
    assert 'non-utf-8' in out


def test_main_check_mode(tmpdir, capsys):
    """Test --check mode doesn't modify files."""
    f = tmpdir.join('f.py')
    f.write('from collections import Mapping\n')
    assert main((f.strpath, '--check')) == 1
    out, err = capsys.readouterr()
    assert 'would be rewritten' in out
    # File should not be modified
    assert f.read() == 'from collections import Mapping\n'


def test_main_check_mode_no_changes(tmpdir, capsys):
    """Test --check mode with no changes."""
    f = tmpdir.join('f.py')
    f.write('from collections.abc import Mapping\n')
    assert main((f.strpath, '--check')) == 0


def test_main_removed_modules(tmpdir, capsys):
    """Test that removed modules are detected and reported."""
    f = tmpdir.join('f.py')
    f.write('import distutils\n')
    assert main((f.strpath,)) == 2  # EXIT_FATAL
    out, err = capsys.readouterr()
    assert 'distutils' in err
    assert 'removed' in err.lower()


def test_main_stdin_no_changes(capsys):
    stdin = io.TextIOWrapper(io.BytesIO(b'x = 1\n'), 'UTF-8')
    with mock.patch.object(sys, 'stdin', stdin):
        assert main(('-',)) == 0
    out, err = capsys.readouterr()
    assert out == 'x = 1\n'


def test_main_stdin_with_changes(capsys):
    stdin = io.TextIOWrapper(io.BytesIO(b'from collections import Mapping\n'), 'UTF-8')
    with mock.patch.object(sys, 'stdin', stdin):
        assert main(('-',)) == 1
    out, err = capsys.readouterr()
    assert out == 'from collections.abc import Mapping\n'
