"""Запуск depgraph с локальным учебным реестром (tests/registry).

Использование: python tests/with_registry.py [--port 8000] -- АРГУМЕНТЫ
Сервер доступен по адресу http://localhost:ПОРТ, пока работает depgraph.
"""

import argparse
import functools
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
DEFAULT_PORT = 8000


class QuietHandler(SimpleHTTPRequestHandler):
    """Обработчик HTTP без вывода журнала запросов."""

    def log_message(self, *args):
        """Не печатать журнал."""


def main(argv):
    """Запустить сервер, выполнить depgraph, остановить сервер."""
    import depgraph

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)
    handler = functools.partial(
        QuietHandler, directory=os.path.join(ROOT, "tests", "registry"))
    server = ThreadingHTTPServer(("127.0.0.1", options.port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        return depgraph.main([a for a in options.args if a != "--"])
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
