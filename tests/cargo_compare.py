"""Сравнение depgraph с cargo tree на учебном реестре (нужен cargo).

Из tests/registry собирается настоящий реестр Cargo: для каждой версии
создаётся архив .crate с Cargo.toml (по записи индекса), в индекс
добавляется контрольная сумма, реестр отдаётся по HTTP на localhost.
Затем в пустом проекте запускается ``cargo tree`` и его вывод
сравнивается с выводом depgraph. Всё создаётся во временной папке и
удаляется; в репозитории архивов нет.

Запуск: python tests/cargo_compare.py [пакет [версия [ключи cargo tree]]]
Например: python tests/cargo_compare.py app 1.0.0 --all-features
"""

import functools
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
REGISTRY = os.path.join(ROOT, "tests", "registry")
DEFAULT_PACKAGE = "app"
DEFAULT_VERSION = "1.0.0"
KIND_SECTIONS = {"normal": "dependencies", "dev": "dev-dependencies",
                 "build": "build-dependencies"}


class QuietHandler(SimpleHTTPRequestHandler):
    """HTTP-обработчик без журнала."""

    def log_message(self, *args):
        """Не печатать журнал."""


def dependency_line(dep):
    """Строка зависимости для Cargo.toml."""
    parts = [f'version = "{dep["req"]}"', 'registry = "local"']
    if dep.get("package"):
        parts.append(f'package = "{dep["package"]}"')
    if dep["optional"]:
        parts.append("optional = true")
    if not dep["default_features"]:
        parts.append("default-features = false")
    return f'{dep["name"]} = {{ {", ".join(parts)} }}'


def manifest_text(entry):
    """Cargo.toml по записи индекса."""
    lines = ["[package]", f'name = "{entry["name"]}"',
             f'version = "{entry["vers"]}"', 'edition = "2021"', ""]
    sections = {}
    for dep in entry["deps"]:
        header = KIND_SECTIONS[dep["kind"]]
        if dep.get("target"):
            header = f"target.'{dep['target']}'.{header}"
        sections.setdefault(header, []).append(dependency_line(dep))
    for header, items in sections.items():
        lines += [f"[{header}]"] + items + [""]
    if entry["features"]:
        lines.append("[features]")
        for name, members in entry["features"].items():
            lines.append(f"{name} = {json.dumps(members)}")
    return "\n".join(lines) + "\n"


def make_crate(entry):
    """Архив .crate (tar.gz) с манифестом и пустой библиотекой."""
    folder = f'{entry["name"]}-{entry["vers"]}'
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, text in (("Cargo.toml", manifest_text(entry)),
                           ("src/lib.rs", "")):
            data = text.encode("utf-8")
            info = tarfile.TarInfo(f"{folder}/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def build_registry(target, port):
    """Собрать реестр Cargo в папке target из tests/registry."""
    shutil.copytree(REGISTRY, target)
    config = {"dl": f"http://127.0.0.1:{port}/dl/{{crate}}/{{version}}.crate"}
    with open(os.path.join(target, "config.json"), "w") as file:
        json.dump(config, file)
    for folder, _, files in os.walk(REGISTRY):
        for name in files:
            if name != "config.json":
                add_crates(target, os.path.join(folder, name))


def add_crates(target, index_file):
    """Создать .crate для каждой версии и дописать cksum в индекс."""
    lines = []
    with open(index_file, encoding="utf-8") as file:
        entries = [json.loads(line) for line in file if line.strip()]
    for entry in entries:
        data = make_crate(entry)
        entry["cksum"] = hashlib.sha256(data).hexdigest()
        path = os.path.join(target, "dl", entry["name"],
                            f'{entry["vers"]}.crate')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as file:
            file.write(data)
        lines.append(json.dumps(entry))
    relative = os.path.relpath(index_file, REGISTRY)
    with open(os.path.join(target, relative), "w", encoding="utf-8") as out:
        out.write("\n".join(lines) + "\n")


def cargo_tree(work, port, package, version, extra):
    """Запустить cargo tree в проекте, зависящем от package."""
    project = os.path.join(work, "check")
    os.makedirs(os.path.join(project, "src"), exist_ok=True)
    os.makedirs(os.path.join(project, ".cargo"), exist_ok=True)
    with open(os.path.join(project, "src", "lib.rs"), "w") as file:
        file.write("")
    with open(os.path.join(project, "Cargo.toml"), "w") as file:
        file.write('[package]\nname = "check"\nversion = "0.0.0"\n'
                   'edition = "2021"\n\n[dependencies]\n'
                   f'{package} = {{ version = "={version}", '
                   'registry = "local" }\n')
    with open(os.path.join(project, ".cargo", "config.toml"), "w") as file:
        file.write(f'[registries.local]\nindex = "sparse+http://127.0.0.1:'
                   f'{port}/"\n')
    env = dict(os.environ, CARGO_HOME=os.path.join(work, "home"),
               NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
    command = ["cargo", "tree", "-p", package, *extra]
    result = subprocess.run(command, cwd=project, env=env, text=True,
                            capture_output=True)
    return result.stdout if result.returncode == 0 else result.stderr


def depgraph_output(port, package, version):
    """Вывод depgraph для того же пакета (через тот же реестр)."""
    import depgraph
    config = os.path.join(tempfile.gettempdir(), "compare_config.yaml")
    with open(config, "w") as file:
        file.write(f"package: {package}\nrepository: http://127.0.0.1:{port}"
                   f"\ntest_mode: false\nversion: {version}\nfilter: \"\"\n")
    buffer = io.StringIO()
    stdout, sys.stdout = sys.stdout, buffer
    try:
        depgraph.main(["--config", config, "--action", "graph"])
    finally:
        sys.stdout = stdout
    return buffer.getvalue()


def main(argv):
    """Собрать реестр, вывести результаты cargo tree и depgraph."""
    package = argv[0] if argv else DEFAULT_PACKAGE
    version = argv[1] if len(argv) > 1 else DEFAULT_VERSION
    if shutil.which("cargo") is None:
        print("cargo не найден: сравнение невозможно")
        return 1
    with tempfile.TemporaryDirectory() as work:
        handler_dir = os.path.join(work, "registry")
        server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(
            QuietHandler, directory=handler_dir))
        port = server.server_address[1]
        build_registry(handler_dir, port)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print("=== depgraph (граф зависимостей) ===")
        print(depgraph_output(port, package, version))
        variants = [("cargo tree -e normal", ["-e", "normal"]),
                    ("cargo tree (по умолчанию)", [])]
        if argv[2:]:
            variants = [(f"cargo tree {' '.join(argv[2:])}", argv[2:])]
        for title, extra in variants:
            print(f"=== {title} ===")
            print(cargo_tree(work, port, package, version, extra))
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
