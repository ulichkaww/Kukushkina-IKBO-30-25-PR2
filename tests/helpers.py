"""Общие вспомогательные функции для тестов."""

import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))


def path(*parts):
    """Абсолютный путь внутри проекта."""
    return os.path.join(ROOT, *parts)


def run_main(func, argv):
    """Вызвать func(argv): вернуть (код, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = func(argv)
    return code, out.getvalue(), err.getvalue()
