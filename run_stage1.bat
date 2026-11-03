@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo === Параметры из корректных конфигураций
python src\depgraph.py --config configs\test_tree.yaml
echo.
python src\depgraph.py --config configs\real_regex.yaml

echo.
echo === Ошибка: конфигурационный файл не найден
python src\depgraph.py --config nofile.yaml

for %%f in (tests\configs\*.yaml) do (
    echo.
    echo === Ошибка в %%f
    python src\depgraph.py --config %%f
)

pause
