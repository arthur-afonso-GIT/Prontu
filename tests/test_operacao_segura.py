import unittest

from utils.operacao_segura import (
    finalizar_operacao,
    iniciar_operacao,
    mensagem_erro_usuario,
)


class BotaoFalso:
    def __init__(self, texto="Salvar"):
        self._texto = texto
        self._habilitado = True
        self._propriedades = {}

    def property(self, chave):
        return self._propriedades.get(chave)

    def setProperty(self, chave, valor):
        self._propriedades[chave] = valor

    def text(self):
        return self._texto

    def setText(self, texto):
        self._texto = texto

    def setEnabled(self, habilitado):
        self._habilitado = habilitado


class OperacaoSeguraTests(unittest.TestCase):
    def test_bloqueia_duplo_clique_e_restaura_botao(self):
        botao = BotaoFalso()
        self.assertTrue(iniciar_operacao(botao, "Salvando..."))
        self.assertFalse(iniciar_operacao(botao, "Salvando..."))
        self.assertEqual(botao.text(), "Salvando...")
        self.assertFalse(botao._habilitado)

        finalizar_operacao(botao)
        self.assertEqual(botao.text(), "Salvar")
        self.assertTrue(botao._habilitado)

    def test_mensagem_usuario_nao_expoe_detalhes_tecnicos(self):
        mensagem = mensagem_erro_usuario("salvar o paciente")
        self.assertIn("Não foi possível salvar o paciente", mensagem)
        self.assertNotIn("Supabase", mensagem)
        self.assertNotIn("traceback", mensagem.lower())


if __name__ == "__main__":
    unittest.main()
