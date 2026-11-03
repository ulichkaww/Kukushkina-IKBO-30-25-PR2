"""Общие вспомогательные функции для тестов."""

import functools
import io
import os
import sys
import threading
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

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



class QuietHandler(SimpleHTTPRequestHandler):
    """Обработчик HTTP без вывода журнала запросов."""

    def log_message(self, *args):
        """Не печатать журнал."""


@contextmanager
def registry_url():
    """Запустить локальный сервер tests/registry; выдать его URL."""
    handler = functools.partial(
        QuietHandler, directory=path("tests", "registry"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
