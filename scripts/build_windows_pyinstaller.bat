@echo off
REM ============================================================
REM  Script de build do Clinic Manager via PyInstaller (Windows)
REM ============================================================
REM  Uso: execute este arquivo a partir da raiz do projeto, com o
REM  ambiente virtual ja ativado:
REM
REM      scripts\build_windows_pyinstaller.bat
REM
REM  O executavel final sera gerado em dist\ClinicManager.exe
REM ============================================================

echo.
echo === Limpando builds anteriores ===
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo.
echo === Verificando PyInstaller ===
pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo PyInstaller nao encontrado. Instalando...
    pip install pyinstaller
)

echo.
echo === Gerando executavel (--onefile --windowed) ===
pyinstaller build_config.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo *** ERRO: a geracao do executavel falhou. Veja o log acima. ***
    exit /b 1
)

echo.
echo === Build concluido com sucesso! ===
echo Executavel disponivel em: dist\ClinicManager.exe
echo.
pause
