@echo off
REM ============================================================
REM  Script de configuracao inicial do ambiente (Windows)
REM ============================================================
REM  Cria o ambiente virtual, instala as dependencias e inicializa
REM  o banco de dados. Execute uma unica vez ao clonar o projeto.
REM
REM  Uso: scripts\setup_dev_environment.bat
REM ============================================================

echo.
echo === Criando ambiente virtual (venv) ===
python -m venv venv

echo.
echo === Ativando ambiente virtual ===
call venv\Scripts\activate.bat

echo.
echo === Atualizando pip ===
python -m pip install --upgrade pip

echo.
echo === Instalando dependencias do requirements.txt ===
pip install -r requirements.txt

echo.
echo === Ambiente configurado com sucesso! ===
echo Para ativar o ambiente em uma nova sessao do terminal, execute:
echo     venv\Scripts\activate.bat
echo.
echo Para executar a aplicacao:
echo     python main.py
echo.
pause
