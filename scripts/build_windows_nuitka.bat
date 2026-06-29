@echo off
REM ============================================================
REM  Script de build do Clinic Manager via Nuitka (Windows)
REM ============================================================
REM  Nuitka compila o Python para C/C++ e gera um binario nativo,
REM  geralmente com tempo de inicializacao mais rapido que o
REM  PyInstaller, ao custo de um tempo de build mais longo.
REM
REM  Uso: execute a partir da raiz do projeto, com o ambiente
REM  virtual ja ativado:
REM
REM      scripts\build_windows_nuitka.bat
REM ============================================================

echo.
echo === Verificando Nuitka ===
pip show nuitka >nul 2>nul
if errorlevel 1 (
    echo Nuitka nao encontrado. Instalando...
    pip install nuitka
)

echo.
echo === Limpando builds anteriores ===
rmdir /s /q main.dist 2>nul
rmdir /s /q main.build 2>nul
rmdir /s /q main.onefile-build 2>nul

echo.
echo === Compilando com Nuitka (--onefile --windows-disable-console) ===
python -m nuitka ^
    --onefile ^
    --windows-console-mode=disable ^
    --enable-plugin=pyside6 ^
    --include-data-dir=assets=assets ^
    --output-filename=ClinicManager.exe ^
    --windows-icon-from-ico=assets\icons\app_icon.ico ^
    --company-name="ClinicManager" ^
    --product-name="Clinic Manager" ^
    --file-version=1.0.0.0 ^
    --product-version=1.0.0.0 ^
    main.py

if errorlevel 1 (
    echo.
    echo *** ERRO: a compilacao com Nuitka falhou. Veja o log acima. ***
    exit /b 1
)

echo.
echo === Build concluido com sucesso! ===
echo Executavel disponivel em: ClinicManager.exe
echo.
pause
