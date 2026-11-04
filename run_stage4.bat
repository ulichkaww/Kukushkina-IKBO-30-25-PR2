@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo === 1. Дерево: кто зависит от D (tests\repos\tree.txt)
python src\depgraph.py --config configs\reverse_tree.yaml --action reverse
echo.
echo === 2. Ромб: кто зависит от E
python src\depgraph.py --config configs\reverse_diamond.yaml --action reverse
echo.
echo === 3. Цикл: кто зависит от C
python src\depgraph.py --config configs\reverse_cycle.yaml --action reverse
echo.
echo === 4. Пакет зависит сам от себя
python src\depgraph.py --config configs\reverse_self_cycle.yaml --action reverse
echo.
echo === 5. Фильтр "B": BA не учитывается
python src\depgraph.py --config configs\reverse_filter.yaml --action reverse
echo.
echo === 6. Большой граф: кто зависит от K
python src\depgraph.py --config configs\reverse_big.yaml --action reverse
echo.
echo === 7. От пакета A никто не зависит
python src\depgraph.py --config configs\reverse_none.yaml --action reverse

echo.
echo === Ошибки режима reverse
for %%f in (tests\reverse_configs\*.yaml) do (
    echo --- %%f
    python src\depgraph.py --config %%f --action reverse
)

pause
