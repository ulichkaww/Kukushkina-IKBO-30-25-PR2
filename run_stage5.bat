@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo === 1. Текст Mermaid: граф с циклом (пунктир — ребро, замыкающее цикл)
python src\depgraph.py --config configs\test_cycle.yaml --action mermaid
echo.
echo === 2. Текст Mermaid: большой тестовый граф
python src\depgraph.py --config configs\test_big.yaml --action mermaid
echo.
echo === 3. Изображение тестового графа (нужен интернет: mermaid.ink)
python src\depgraph.py --config configs\test_big.yaml --action image
echo.
echo === 4. Три пакета учебного реестра: app, util, libx
python tests\with_registry.py -- --config configs\registry_app.yaml --action image --output output\app.png
python tests\with_registry.py -- --config configs\registry_util.yaml --action image --output output\util.png
python tests\with_registry.py -- --config configs\registry_libx.yaml --action image --output output\libx.png
echo.
echo === 5. Реальные пакеты crates.io: regex, rand, clap (нужен интернет)
python src\depgraph.py --config configs\real_regex.yaml --action image --output output\regex.png
python src\depgraph.py --config configs\real_rand.yaml --action image --output output\rand.png
python src\depgraph.py --config configs\real_clap.yaml --action image --output output\clap.png
echo.
echo === Сравнение с cargo tree (нужен установленный cargo)
python tests\cargo_compare.py app 1.0.0

pause
