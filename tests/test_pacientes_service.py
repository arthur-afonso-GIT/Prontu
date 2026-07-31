from services.pacientes_service import (
    data_br_para_iso,
    data_iso_para_br,
    formatar_cpf,
    formatar_rg,
    formatar_telefone,
    normalizar_estado_civil,
    normalizar_rg,
    paciente_corresponde_busca,
    somente_numeros,
)


def test_busca_por_nome_considera_inicio_e_ignora_acentos():
    paciente = {"nome": "João Souza", "telefone": "81999990000"}
    assert paciente_corresponde_busca(paciente, "joa")
    assert not paciente_corresponde_busca(paciente, "sou")


def test_busca_numerica_considera_documentos_e_telefone():
    paciente = {
        "nome": "Maria",
        "telefone": "(81) 99999-0000",
        "cpf": "123.456.789-00",
        "rg": "998877",
    }
    assert paciente_corresponde_busca(paciente, "999900")
    assert paciente_corresponde_busca(paciente, "456789")
    assert paciente_corresponde_busca(paciente, "8877")


def test_normalizacao_e_conversao_de_data():
    assert somente_numeros("123.456.789-00", 11) == "12345678900"
    assert data_br_para_iso("28/07/2026") == "2026-07-28"
    assert data_br_para_iso("28072026") == "2026-07-28"
    assert data_br_para_iso("2026-07-28") == "2026-07-28"
    assert data_br_para_iso("31/02/2026") is None
    assert data_iso_para_br("2026-07-28") == "28/07/2026"


def test_formatacao_visual_de_documentos_e_telefone():
    assert formatar_telefone("81991214670") == "(81) 99121-4670"
    assert formatar_telefone("8133224455") == "(81) 3322-4455"
    assert formatar_cpf("12345678900") == "123.456.789-00"
    assert normalizar_rg("12.345.678-x") == "12345678X"
    assert formatar_rg("123456789") == "12.345.678-9"
    assert formatar_rg("MG-12.345.678") == "MG12345678"


def test_estado_civil_legado_e_convertido_para_opcao_padrao():
    assert normalizar_estado_civil("casada") == "Casado(a)"
    assert normalizar_estado_civil("União Estável") == "União estável"
    assert normalizar_estado_civil("") == "Não informado"
