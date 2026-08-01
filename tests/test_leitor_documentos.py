from services import leitor_documentos
from services.leitor_documentos import (
    BlocoDocumento,
    interpretar_blocos,
    interpretar_ficha_preenchida,
)
from services.fichas_service import normalizar_estrutura


def campo_por_label(campos, label):
    return next(campo for campo in campos if campo["label"] == label)


def test_interpreta_tipos_clinicos_e_preserva_ordem():
    campos = interpretar_blocos([
        BlocoDocumento("IDENTIFICAÇÃO", nivel_titulo=1),
        "Nome completo:",
        "Data de nascimento: __/__/____",
        "Peso:",
        "HISTÓRICO CLÍNICO",
        "Queixa principal:",
        "Exemplo: descreva quando os sintomas começaram.",
    ])

    assert [campo["label"] for campo in campos] == [
        "IDENTIFICAÇÃO",
        "Nome completo",
        "Data de nascimento",
        "Peso",
        "HISTÓRICO CLÍNICO",
        "Queixa principal",
    ]
    assert campo_por_label(campos, "Nome completo")["tipo"] == "texto_curto"
    assert campo_por_label(campos, "Data de nascimento")["tipo"] == "data"
    assert campo_por_label(campos, "Peso") == {
        "tipo": "numero", "label": "Peso", "id": "peso", "unidade": "kg",
    }
    queixa = campo_por_label(campos, "Queixa principal")
    assert queixa["tipo"] == "texto_longo"
    assert queixa["placeholder"].startswith("Exemplo:")


def test_interpreta_multipla_escolha_inline_e_em_linhas_separadas():
    campos = interpretar_blocos([
        "Sexo biológico: ( ) Feminino ( ) Masculino ( ) Outro",
        "Estado civil:",
        "( ) Solteiro",
        "[ ] Casado",
        "☐ Outro",
    ])

    sexo = campo_por_label(campos, "Sexo biológico")
    assert sexo["tipo"] == "multipla_escolha"
    assert sexo["opcoes"] == ["Feminino", "Masculino", "Outro"]

    estado = campo_por_label(campos, "Estado civil")
    assert estado["tipo"] == "multipla_escolha"
    assert estado["opcoes"] == ["Solteiro", "Casado", "Outro"]


def test_reconhece_checkbox_e_remove_duplicata_exata():
    campos = interpretar_blocos([
        "Paciente autoriza compartilhamento: [ ]",
        "Telefone:",
        "Telefone:",
    ])

    autorizacao = campo_por_label(campos, "Paciente autoriza compartilhamento")
    assert autorizacao["tipo"] == "checkbox"
    assert autorizacao["texto_checkbox"] == "Paciente autoriza compartilhamento"
    assert sum(campo["label"] == "Telefone" for campo in campos) == 1


def test_nao_transforma_frase_explicitiva_em_campo():
    campos = interpretar_blocos([
        "Preencha os dados abaixo com atenção.",
        "Nome:",
        "Esta frase apenas explica o formulário e não é uma pergunta.",
    ])

    assert [campo["label"] for campo in campos] == ["Nome"]


def test_celula_de_tabela_curta_e_reconhecida_como_campo():
    campos = interpretar_blocos([
        BlocoDocumento("Profissão", origem="tabela:1:1"),
        BlocoDocumento("Convênio", origem="tabela:1:2"),
    ])

    assert [campo["label"] for campo in campos] == ["Profissão", "Convênio"]
    assert all(campo["tipo"] == "texto_curto" for campo in campos)


def test_importacao_liga_data_generica_a_idade_e_reconhece_contatos():
    campos = normalizar_estrutura(interpretar_blocos([
        "Data:",
        "Idade:",
        "Telefone:",
        "CPF:",
        "RG:",
    ]))

    data = campo_por_label(campos, "Data")
    idade = campo_por_label(campos, "Idade")
    assert data["semantica"] == "data_nascimento"
    assert idade["calculado_por"] == data["id"]
    assert campo_por_label(campos, "Telefone")["semantica"] == "telefone"
    assert campo_por_label(campos, "CPF")["semantica"] == "cpf"
    assert campo_por_label(campos, "RG")["semantica"] == "rg"


def test_digitalizacao_associa_campos_e_respostas_em_linhas_separadas():
    resultado = interpretar_ficha_preenchida([
        BlocoDocumento("IDENTIFICAÇÃO", nivel_titulo=1, confianca=0.99),
        BlocoDocumento("Nome completo:", confianca=0.98),
        BlocoDocumento("Arthur Florêncio", confianca=0.96),
        BlocoDocumento("Data de nascimento: 16052007", confianca=0.94),
        BlocoDocumento("Telefone", confianca=0.97),
        BlocoDocumento("81992124670", confianca=0.95),
    ])

    campos = normalizar_estrutura(resultado.campos)
    nome = campo_por_label(campos, "Nome completo")
    nascimento = campo_por_label(campos, "Data de nascimento")
    telefone = campo_por_label(campos, "Telefone")
    assert resultado.respostas[nome["id"]] == "Arthur Florêncio"
    assert resultado.respostas[nascimento["id"]] == "16052007"
    assert resultado.respostas[telefone["id"]] == "81992124670"
    assert nascimento["semantica"] == "data_nascimento"
    assert telefone["semantica"] == "telefone"


def test_digitalizacao_reconhece_opcao_marcada_e_preserva_texto_solto():
    resultado = interpretar_ficha_preenchida([
        "Sexo biológico: [ ] Feminino [x] Masculino [ ] Outro",
        "Queixa principal: Dor lombar há três dias",
        "Trecho manuscrito que não foi associado",
    ])

    sexo = campo_por_label(resultado.campos, "Sexo biológico")
    queixa = campo_por_label(resultado.campos, "Queixa principal")
    adicional = campo_por_label(resultado.campos, "Conteúdo adicional reconhecido")
    assert sexo["tipo"] == "multipla_escolha"
    assert sexo["opcoes"] == ["Feminino", "Masculino", "Outro"]
    assert resultado.respostas[sexo["id"]] == "Masculino"
    assert resultado.respostas[queixa["id"]] == "Dor lombar há três dias"
    assert "Trecho manuscrito" in resultado.respostas[adicional["id"]]
    assert resultado.avisos


def test_digitalizacao_sinaliza_baixa_confianca_sem_descartar_resposta():
    resultado = interpretar_ficha_preenchida([
        BlocoDocumento("CPF: 12345678901", confianca=0.61),
    ])

    cpf = campo_por_label(resultado.campos, "CPF")
    assert resultado.respostas[cpf["id"]] == "12345678901"
    assert "baixa confiança" in cpf["ajuda"].lower()
    assert "1 campo" in resultado.avisos[0]


def test_digitalizacao_cria_selecao_quando_opcoes_nao_tem_titulo():
    resultado = interpretar_ficha_preenchida([
        "[x] Hipertensao [ ] Diabetes",
    ])

    campo = campo_por_label(resultado.campos, "Opções identificadas")
    assert campo["tipo"] == "multipla_escolha"
    assert campo["opcoes"] == ["Hipertensao", "Diabetes"]
    assert resultado.respostas[campo["id"]] == "Hipertensao"


def test_digitalizacao_relaciona_campos_em_colunas_pelas_coordenadas():
    resultado = interpretar_ficha_preenchida([
        BlocoDocumento(
            "Nome completo:", pagina=1, x=20, y=20,
            largura=120, altura=20, confianca=0.98,
        ),
        BlocoDocumento(
            "CPF:", pagina=1, x=340, y=20,
            largura=45, altura=20, confianca=0.99,
        ),
        BlocoDocumento(
            "Maria Silva", pagina=1, x=20, y=55,
            largura=150, altura=20, confianca=0.96,
        ),
        BlocoDocumento(
            "12345678901", pagina=1, x=340, y=55,
            largura=130, altura=20, confianca=0.97,
        ),
    ])

    nome = campo_por_label(resultado.campos, "Nome completo")
    cpf = campo_por_label(resultado.campos, "CPF")
    assert resultado.respostas[nome["id"]] == "Maria Silva"
    assert resultado.respostas[cpf["id"]] == "12345678901"
    assert "Conteúdo adicional reconhecido" not in {
        campo["label"] for campo in resultado.campos
    }


def test_digitalizacao_separa_varios_campos_reconhecidos_na_mesma_linha():
    resultado = interpretar_ficha_preenchida([
        "Nome: Maria Silva  CPF: 12345678901  Telefone: 81992124670",
    ])

    nome = campo_por_label(resultado.campos, "Nome")
    cpf = campo_por_label(resultado.campos, "CPF")
    telefone = campo_por_label(resultado.campos, "Telefone")
    assert resultado.respostas[nome["id"]] == "Maria Silva"
    assert resultado.respostas[cpf["id"]] == "12345678901"
    assert resultado.respostas[telefone["id"]] == "81992124670"


def test_ocr_aceita_matrizes_da_versao_atual_do_rapidocr(monkeypatch):
    import numpy as np

    class ResultadoFake:
        txts = np.array(["Nome: Maria"])
        boxes = np.array([[[10, 10], [210, 10], [210, 50], [10, 50]]])
        scores = np.array([0.97])

    monkeypatch.setattr(
        leitor_documentos,
        "_obter_motor_ocr",
        lambda: (lambda _caminho: ResultadoFake()),
    )
    monkeypatch.setattr(
        leitor_documentos,
        "_preparar_imagem_ocr",
        lambda _origem, _destino: None,
    )

    blocos = leitor_documentos._executar_ocr_imagem("ficha.png")

    assert len(blocos) == 1
    assert blocos[0].texto == "Nome: Maria"
    assert blocos[0].confianca == 0.97
    assert blocos[0].largura == 200
