from services.fichas_service import (
    exportar_ficha_word,
    html_exportacao_ficha,
    nome_arquivo_exportacao,
    normalizar_estrutura,
    preparar_dados_exportacao,
    respostas_iniciais,
    validar_respostas,
)


def test_normaliza_campos_e_remove_identificador_do_rotulo():
    campos = normalizar_estrutura([
        {
            "tipo": "texto_longo",
            "id": "custom_35f06f7e_prescricoes",
            "label": "35f06f7e prescrições",
            "obrigatorio": True,
        },
        {
            "tipo": "multipla_escolha",
            "label": "Conduta",
            "opcoes": [" Observar ", "", "Encaminhar"],
        },
    ])

    assert campos[0]["label"] == "prescrições"
    assert campos[0]["obrigatorio"] is True
    assert campos[1]["id"].startswith("campo_1_conduta")
    assert campos[1]["opcoes"] == ["Observar", "Encaminhar"]


def test_respostas_iniciais_respeitam_checkbox_e_data():
    campos = normalizar_estrutura([
        {"tipo": "checkbox", "id": "fumante", "label": "Fumante"},
        {
            "tipo": "data",
            "id": "data_consulta",
            "label": "Data",
            "preencher_hoje": True,
        },
    ])

    respostas = respostas_iniciais(campos)

    assert respostas["fumante"] is False
    assert len(respostas["data_consulta"].split("/")) == 3


def test_validacao_informa_campos_obrigatorios():
    campos = normalizar_estrutura([
        {
            "tipo": "texto_curto",
            "id": "queixa",
            "label": "Queixa principal",
            "obrigatorio": True,
        },
        {
            "tipo": "texto_longo",
            "id": "observacao",
            "label": "Observação",
        },
    ])

    assert validar_respostas(campos, {"queixa": ""}) == (
        False,
        ["Queixa principal"],
    )
    assert validar_respostas(campos, {"queixa": "Dor lombar"}) == (True, [])


def test_exportacao_preserva_secoes_respostas_e_escapa_html():
    campos = [
        {"tipo": "secao", "label": "Consulta"},
        {"tipo": "texto_longo", "id": "qp", "label": "Queixa"},
        {"tipo": "checkbox", "id": "autorizou", "label": "Autorizou"},
    ]
    dados = preparar_dados_exportacao(
        campos,
        {"qp": "Dor <forte>", "autorizou": True},
        "Maria da Silva",
        "Consulta geral",
        "Clínica Prontu",
        "Dra. Laura",
        "29/07/2026 às 10:00",
    )

    assert dados["itens"][0]["tipo"] == "secao"
    assert dados["itens"][1]["valor"] == "Dor <forte>"
    assert dados["itens"][2]["valor"] == "Sim"
    assert nome_arquivo_exportacao(dados, "pdf").startswith(
        "Ficha_Maria_da_Silva_"
    )
    conteudo = html_exportacao_ficha(dados)
    assert "Dor &lt;forte&gt;" in conteudo
    assert "Clínica Prontu" in conteudo


def test_exportacao_word_cria_documento_valido(tmp_path):
    dados = preparar_dados_exportacao(
        [{"tipo": "texto_curto", "id": "qp", "label": "Queixa"}],
        {"qp": "Avaliação de rotina"},
        "Maria da Silva",
        "Consulta geral",
    )
    destino = tmp_path / "ficha.docx"

    exportar_ficha_word(dados, destino)

    assert destino.read_bytes().startswith(b"PK")
    assert destino.stat().st_size > 1000
