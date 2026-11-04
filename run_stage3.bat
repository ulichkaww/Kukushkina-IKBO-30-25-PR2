@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo === 1. Дерево без повторов (tests\repos\tree.txt)
python src\depgraph.py --config configs\test_tree.yaml
echo.
echo === 2. Ромб: общая зависимость D показана один раз (*)
python src\depgraph.py --config configs\test_diamond.yaml
echo.
echo === 3. Цикл A -^> B -^> C -^> A
python src\depgraph.py --config configs\test_cycle.yaml
echo.
echo === 4. Пакет зависит сам от себя
python src\depgraph.py --config configs\test_self_cycle.yaml
echo.
echo === 5. Фильтр "B": пакеты BA и BB не учитываются
python src\depgraph.py --config configs\test_filter.yaml
echo.
echo === 6. Несвязанные пакеты не попадают в граф
python src\depgraph.py --config configs\test_disconnected.yaml
echo.
echo === 7. Большой граф с двумя циклами
python src\depgraph.py --config configs\test_big.yaml
echo.
echo === 8. Прямые зависимости (--action direct)
python src\depgraph.py --config configs\test_big.yaml --action direct

echo.
echo === Ошибки тестового репозитория и фильтра
for %%f in (tests\graph_configs\*.yaml) do (
    echo --- %%f
    python src\depgraph.py --config %%f
)

echo.
echo === Учебный реестр (формат crates.io), транзитивные зависимости
python tests\with_registry.py -- --config configs\local_registry.yaml

echo.
echo === Реальный crates.io (нужен интернет): regex, rand, clap
python src\depgraph.py --config configs\real_regex.yaml
python src\depgraph.py --config configs\real_rand.yaml
python src\depgraph.py --config configs\real_clap.yaml

pause
