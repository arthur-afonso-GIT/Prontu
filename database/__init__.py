# ==========================================
#  database/__init__.py
# ==========================================
# Este arquivo expõe a classe Database para o resto do projeto,
# resolvendo o conflito de importação com a pasta 'database'.

import os
import sys

# Garante que o diretório raiz esteja no caminho de busca do Python
raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if raiz_projeto not in sys.path:
    sys.path.insert(0, raiz_projeto)

# Tenta importar do arquivo de banco de dados
try:
    from database.database import Database
except ImportError:
    try:
        from database import Database
    except ImportError:
        # Fallback caso o arquivo database.py esteja na raiz
        import database
        if hasattr(database, 'Database'):
            Database = database.Database
        else:
            raise ImportError("Não foi possível localizar a classe 'Database' no módulo 'database'.")