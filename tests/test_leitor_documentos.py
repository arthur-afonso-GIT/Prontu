from services.leitor_documentos import BlocoDocumento, interpretar_blocos


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
