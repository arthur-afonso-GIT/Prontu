import sqlite3
import os

class Database:
    def __init__(self, db_name="prontu.db"):
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
        
        # 2. Tabela de Agendamentos (Ligada ao ID do paciente)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_nome TEXT NOT NULL,
                data TEXT NOT NULL,
                horario TEXT NOT NULL,
                duracao TEXT,
                procedimento TEXT,
                status TEXT,
                observacoes TEXT
            )
        """)
        
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