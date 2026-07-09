import sqlite3
import os

class Database:
    def __init__(self, db_name=None):
        """Inicialização segura comercial na pasta AppData do usuário."""
        if db_name is None:
            appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            pasta_app = os.path.join(appdata, "ProntuApp")
            if not os.path.exists(pasta_app):
                os.makedirs(pasta_app)
            self.db_name = os.path.join(pasta_app, "prontu.db")
        else:
            self.db_name = db_name
            
        self.init_db()

    def conectar(self):
        """Abre a conexão com o banco de dados local."""
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Cria as tabelas iniciais se elas não existirem no computador."""
        conn = self.conectar()
        cursor = conn.cursor()
        
        # 1. Tabela de Pacientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                nascimento TEXT,
                convenio TEXT,
                endereco TEXT,
                queixa_principal TEXT,
                pasta TEXT DEFAULT 'Geral'
            )
        """)
        
        # 2. Tabela de Agendamentos estruturada para persistência em JSON
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agendamentos (
                data TEXT,
                hora TEXT,
                dados TEXT,
                PRIMARY KEY (data, hora)
            )
        """)
        
        # 3. Tabela de Configurações do Sistema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)
        
        conn.commit()
        conn.close()

    # --- FUNÇÕES DE CONFIGURAÇÃO (Sincronizadas em Português) ---
    def obter_nome_profissional(self):
        """Recupera o nome salvo do médico/profissional."""
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'nome_profissional'")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""

    def salvar_nome_profissional(self, nome):
        """Salva ou atualiza o nome do médico/profissional."""
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO configuracoes (chave, valor)
            VALUES ('nome_profissional', ?)
        """, (nome.strip(),))
        conn.commit()
        conn.close()

    # --- FUNÇÕES PARA PACIENTES ---
    def salvar_paciente(self, dados):
        """Insere um novo paciente no banco de dados."""
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pacientes (nome, telefone, nascimento, convenio, endereco, queixa_principal, pasta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dados['nome'], dados['telefone'], dados['nascimento'], dados['convenio'], dados['endereco'], dados['queixa_principal'], dados['pasta']))
        conn.commit()
        conn.close()

    def listar_todos_pacientes(self):
        """Retorna todos os pacientes cadastrados."""
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT nome, telefone, convenio, pasta, nascimento, endereco, queixa_principal FROM pacientes ORDER BY nome ASC")
        pacientes = cursor.fetchall()
        conn.close()
        return pacientes

    def buscar_nomes_pacientes(self):
        """Retorna apenas a lista de strings com os nomes (Perfeito para a Agenda!)."""
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM pacientes ORDER BY nome ASC")
        nomes = [row[0] for row in cursor.fetchall()]
        conn.close()
        return nomes