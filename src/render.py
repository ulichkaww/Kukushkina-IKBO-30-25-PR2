"""Получение и показ изображения по тексту Mermaid."""

import base64
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from errors import DepGraphError

INK_URL = "https://mermaid.ink/img/"
USER_AGENT = "depgraph-student-project"
TIMEOUT_SECONDS = 30
MMDC_TIMEOUT_SECONDS = 120
RENDERERS = ("ink", "mmdc")
DEFAULT_RENDERER = "ink"
OUTPUT_DIR = "output"


class RenderError(DepGraphError):
    """Не удалось получить изображение графа."""


def default_paths(package):
    """Пути по умолчанию: output/<пакет>.png и output/<пакет>.mmd."""
    return Path(OUTPUT_DIR) / f"{package}.png"


def save_text(text, png_path):
    """Сохранить текст диаграммы рядом с изображением (.mmd)."""
    mmd_path = Path(png_path).with_suffix(".mmd")
    mmd_path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text(text, encoding="utf-8")
    return mmd_path


def ink_url(text):
    """Адрес изображения на сервисе mermaid.ink для текста диаграммы."""
    code = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")
    return f"{INK_URL}{code}?type=png&bgColor=!white"


def fetch_png(text):
    """Скачать PNG с сервиса mermaid.ink (нужен доступ в интернет)."""
    request = urllib.request.Request(
        ink_url(text), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(
                request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except urllib.error.HTTPError as err:
        raise RenderError(
            f"сервис mermaid.ink ответил: HTTP {err.code}") from err
    except (urllib.error.URLError, OSError) as err:
        raise RenderError(f"нет доступа к mermaid.ink: {err}") from err


def render_with_ink(text, png_path):
    """Получить изображение через mermaid.ink и записать в файл."""
    Path(png_path).write_bytes(fetch_png(text))


def render_with_mmdc(mmd_path, png_path):
    """Получить изображение локальной утилитой mmdc (Mermaid CLI)."""
    program = shutil.which("mmdc")
    if program is None:
        raise RenderError("утилита mmdc не найдена (npm i -g "
                          "@mermaid-js/mermaid-cli)")
    try:
        subprocess.run([program, "-i", str(mmd_path), "-o", str(png_path)],
                       check=True, capture_output=True,
                       timeout=MMDC_TIMEOUT_SECONDS)
    except (subprocess.SubprocessError, OSError) as err:
        raise RenderError(f"mmdc завершилась с ошибкой: {err}") from err


def render_image(text, png_path, renderer=DEFAULT_RENDERER):
    """Сохранить .mmd и изображение; вернуть путь к изображению."""
    mmd_path = save_text(text, png_path)
    try:
        if renderer == "mmdc":
            render_with_mmdc(mmd_path, png_path)
        else:
            render_with_ink(text, png_path)
    except RenderError as err:
        raise RenderError(
            f"{err}. Текст диаграммы сохранён: {mmd_path} "
            "(его можно открыть на https://mermaid.live)") from err
    return Path(png_path)


def show_image(path):
    """Показать изображение: программой по умолчанию или в браузере."""
    if sys.platform == "win32":
        os.startfile(str(path))
    else:
        webbrowser.open(Path(path).resolve().as_uri())
