import os
import sys
from pathlib import Path

# 1. Carrega as variáveis de ambiente do arquivo .env imediatamente
from dotenv import load_dotenv
from utils.diagnostics import configure_diagnostics

_PASTA_APLICACAO = os.path.abspath(os.path.dirname(__file__))
_PASTA_RECURSOS = getattr(sys, "_MEIPASS", _PASTA_APLICACAO)
_CONFIG_PUBLICA = os.path.join(_PASTA_RECURSOS, "prontu_public.env")
_CONFIG_DESENVOLVIMENTO = os.path.join(_PASTA_APLICACAO, ".env")


def _ler_versao() -> str:
    candidatos = (
        Path(_PASTA_RECURSOS) / "VERSION",
        Path(_PASTA_APLICACAO) / "VERSION",
    )
    for caminho in candidatos:
        try:
            versao = caminho.read_text(encoding="utf-8").strip()
            if versao:
                return versao
        except OSError:
            continue
    return "desconhecida"


APP_VERSION = _ler_versao()
logger = configure_diagnostics(APP_VERSION)

if os.path.isfile(_CONFIG_PUBLICA):
    load_dotenv(_CONFIG_PUBLICA, override=False, encoding="utf-8-sig")
if os.path.isfile(_CONFIG_DESENVOLVIMENTO):
    load_dotenv(_CONFIG_DESENVOLVIMENTO, override=True, encoding="utf-8-sig")

# Garante que o diretório atual está no PATH do Python
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox, QDialog
from database import Database
from ui.login_dialog import LoginDialog
from ui.design_system import instalar_design_system
from ui.interaction_feedback import instalar_feedback_interativo


def _importar_main_window():
    """
    Importa a classe MainWindow de forma robusta, independente do diretório
    de trabalho atual ou do estado do sys.path.

    Se a importação normal falhar, tenta localizar o arquivo main_window.py
    diretamente pelo caminho absoluto e carrega o módulo a partir dele.
    Se ainda assim não encontrar, exibe um diagnóstico detalhado explicando
    o motivo exato da falha (arquivo ausente, extensão duplicada, etc.).
    """
    pasta_base = os.path.abspath(os.path.dirname(__file__))

    # Tentativa 1: import padrão (caminho normal, mais rápido)
    try:
        from ui.main_window import MainWindow
        return MainWindow
    except ModuleNotFoundError:
        pass

    # Tentativa 1.5: checa diretamente a raiz do projeto antes de recursar.
    # Isso evita pegar cópias antigas/duplicadas que estejam em subpastas.
    caminho_raiz = os.path.join(pasta_base, "main_window.py")
    if os.path.isfile(caminho_raiz):
        return _carregar_modulo_main_window(caminho_raiz)

    # Tentativa 2: busca dinâmica e recursiva pelo arquivo dentro do projeto,
    # ignorando pastas que nunca contêm código-fonte real (builds, venvs, etc).
    pastas_ignoradas = {
        ".git", "__pycache__", "venv", ".venv", "env",
        "node_modules", "dist", "build", "site-packages",
    }
    encontrados_por_profundidade = {}

    for raiz, subpastas, arquivos in os.walk(pasta_base):
        subpastas[:] = [d for d in subpastas if d not in pastas_ignoradas]
        if "main_window.py" in arquivos:
            caminho = os.path.join(raiz, "main_window.py")
            profundidade = caminho.count(os.sep)
            encontrados_por_profundidade.setdefault(profundidade, []).append(caminho)

    if encontrados_por_profundidade:
        profundidade_minima = min(encontrados_por_profundidade)
        candidatos = encontrados_por_profundidade[profundidade_minima]
        caminho_real = candidatos[0]

        todos_encontrados = [c for lista in encontrados_por_profundidade.values() for c in lista]
        if len(todos_encontrados) > 1:
            print(
                "Aviso: mais de um 'main_window.py' encontrado no projeto (fora de dist/build).\n"
                "Usando o mais próximo da raiz:\n  -> " + caminho_real + "\n"
                "Outras cópias encontradas (considere remover para evitar confusão):\n"
                + "\n".join(f"  - {c}" for c in todos_encontrados if c != caminho_real),
                file=sys.stderr,
            )

        return _carregar_modulo_main_window(caminho_real)

    # Se chegou aqui, o arquivo realmente não existe em NENHUM lugar do projeto.
    try:
        arquivos_na_pasta = os.listdir(pasta_base)
    except Exception as e:
        arquivos_na_pasta = [f"<erro ao listar pasta: {e}>"]

    mensagem = (
        "Não foi possível encontrar 'main_window.py' em nenhuma subpasta de código-fonte de:\n"
        f"  {pasta_base}\n\n"
        "O arquivo não existe fisicamente no disco (fora de pastas de build). Causas mais prováveis:\n"
        "  1) O arquivo foi editado/criado numa conversa com IA (ex: Claude) mas\n"
        "     nunca foi de fato salvo/baixado para este projeto no seu PC;\n"
        "  2) Está sincronizado com o OneDrive como 'somente na nuvem' e ainda\n"
        "     não foi baixado para o disco local;\n"
        "  3) Foi renomeado ou apagado.\n\n"
        "Conteúdo da pasta raiz do projeto:\n"
        + "\n".join(f"  - {f}" for f in sorted(arquivos_na_pasta))
    )

    print(mensagem, file=sys.stderr)
    raise ModuleNotFoundError(mensagem)


def _carregar_modulo_main_window(caminho_arquivo):
    """Carrega o módulo main_window.py a partir de um caminho absoluto específico."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("main_window", caminho_arquivo)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["main_window"] = modulo
    spec.loader.exec_module(modulo)

    # Garante que a pasta onde o arquivo foi achado também entre no
    # sys.path, para o caso de main_window.py importar módulos irmãos
    # (ex: 'from ui.screens.home import HomeScreen' relativos à mesma pasta)
    pasta_do_arquivo = os.path.dirname(caminho_arquivo)
    if pasta_do_arquivo not in sys.path:
        sys.path.insert(0, pasta_do_arquivo)

    return modulo.MainWindow


def inicializar_sistema():
    logger.info("Inicializando interface")
    app = QApplication(sys.argv)
    app.setApplicationName("Prontu")
    app.setOrganizationName("Prontu")
    caminho_icone = os.path.join(_PASTA_RECURSOS, "ui", "assets", "prontu_logo.png")
    if os.path.isfile(caminho_icone):
        app.setWindowIcon(QIcon(caminho_icone))
    instalar_design_system(app)
    instalar_feedback_interativo(app)
    
    # Inicializa o banco de dados principal
    try:
        db = Database()
    except Exception:
        logger.exception("Falha ao inicializar banco e sessão")
        raise
    
    # Se não houver sessão autenticada, solicita a chave
    while not db.esta_autenticado():
        dialogo = LoginDialog(db)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        continue

        chave, ok = QInputDialog.getText(
            None, 
            "Ativação do Sistema — Prontu", 
            "Por favor, insira a Chave de Acesso do seu Consultório:\n"
            "(Ex: PRONTU-DENTISTA-998)"
        )
        
        if not ok:
            sys.exit(0)
            
        chave_limpa = chave.strip()
        if not chave_limpa:
            QMessageBox.warning(None, "Campo Vazio", "A chave não pode estar em branco!")
            continue

        # Valida no Supabase
        resultado = db.validar_chave_acesso(chave_limpa)
        
        if resultado and isinstance(resultado, dict):
            id_detectado = resultado.get("consultorio_id")
            clinica = resultado.get("nome_clinica") or "Seu Consultório"
            
            if id_detectado is not None:
                db.salvar_consultorio_id_local(id_detectado)
                
                QMessageBox.information(
                    None, 
                    "Ativação Concluída", 
                    f"Dispositivo ativado com sucesso!\n\nBem-vindo(a) ao banco de dados da clínica:\n🏥 {clinica}"
                )
            else:
                QMessageBox.critical(
                    None,
                    "Erro de Cadastro",
                    "Esta chave foi validada, mas não possui um ID de consultório associado no banco de dados."
                )
        else:
            QMessageBox.critical(
                None, 
                "Chave Inválida", 
                "A chave inserida não foi encontrada ou está incorreta.\nTente novamente."
            )

    # Importação atrasada (Lazy Import) para evitar conflitos circulares
    MainWindow = _importar_main_window()
    
    # Passamos a conexão configurada para a janela principal
    janela = MainWindow(db)
    janela.show()
    
    exit_code = app.exec()
    logger.info("Aplicativo encerrado | código=%s", exit_code)
    sys.exit(exit_code)

if __name__ == "__main__":
    inicializar_sistema()
