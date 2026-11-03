@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo === Учебный реестр (локальный сервер tests\registry): прямые зависимости app 1.0.0
python tests\with_registry.py -- --config configs\local_registry.yaml
echo.
echo === Другая версия: app 0.9.0
python tests\with_registry.py -- --config tests\registry_configs\old_app.yaml

echo.
echo === Ошибка: пакет не найден
python tests\with_registry.py -- --config tests\registry_configs\nosuch_package.yaml
echo.
echo === Ошибка: версия не найдена
python tests\with_registry.py -- --config tests\registry_configs\unknown_version.yaml
echo.
echo === Ошибка: репозиторий недоступен
python src\depgraph.py --config tests\registry_configs\unreachable.yaml

echo.
echo === Реальный crates.io (нужен интернет): regex, rand, clap
python src\depgraph.py --config configs\real_regex.yaml
python src\depgraph.py --config configs\real_rand.yaml
python src\depgraph.py --config configs\real_clap.yaml

pause
