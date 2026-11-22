@echo off
chcp 65001 >nul
python -m unittest discover -s tests -v
python -m src.assembler tests/spec_test.yaml output.bin --test