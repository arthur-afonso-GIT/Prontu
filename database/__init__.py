# ==========================================
#  database/__init__.py - COMPLETO
# ==========================================
import os
import sys

# 1. Garante que o Python encontre a pasta raiz do projeto corretamente
raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if raiz_projeto not in sys.path:
    sys.path.insert(0, raiz_projeto)

# 2. Importa a classe Database do seu ficheiro principal (database.py)
from database.database import Database

# 3. Expõe a classe para que qualquer ecrã faça apenas "from database import Database"
__all__ = ["Database"]