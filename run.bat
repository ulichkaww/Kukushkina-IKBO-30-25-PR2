@echo off
chcp 65001 > nul
cd /d "%~dp0"

python src\depgraph.py --config configs\test_tree.yaml
pause
