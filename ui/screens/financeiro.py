from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QPushButton,
    QMessageBox,
)
from utils.operacao_segura import (
    finalizar_operacao,
    iniciar_operacao,
    mensagem_erro_usuario,
    registrar_falha,
)


class FinanceiroScreen(QWidget):
    """Controle simples de recebimentos, alimentado por consultas realizadas."""

    def __init__(self, database_instancia):
        super().__init__()
        self.db = database_instancia
        self.registros = []
        self.registro_selecionado = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)

        titulo = QLabel("Financeiro")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a;")
        subtitulo = QLabel("Acompanhe os pagamentos das consultas marcadas como realizadas.")
        subtitulo.setStyleSheet("font-size: 13px; color: #64748b;")
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.card_recebido = self._criar_card("Recebido no mês", "R$ 0,00", "#dcfce7", "#15803d")
        self.card_pendente = self._criar_card("A receber", "R$ 0,00", "#fef3c7", "#b45309")
        self.card_consultas = self._criar_card("Consultas na agenda", "0", "#e0f2fe", "#0369a1")
        cards.addWidget(self.card_recebido)
        cards.addWidget(self.card_pendente)
        cards.addWidget(self.card_consultas)
        cards.addStretch()
        layout.addLayout(cards)

        conteudo = QHBoxLayout()
        conteudo.setSpacing(18)

        coluna_lista = QVBoxLayout()
        lbl_lista = QLabel("Consultas e pagamentos")
        lbl_lista.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        coluna_lista.addWidget(lbl_lista)
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6)
        self.tabela.setHorizontalHeaderLabels(["Data", "Paciente", "Procedimento", "Valor", "Recebido", "Status"])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabela.setStyleSheet("QTableWidget { background: white; border: 1px solid #e2e8f0; border-radius: 8px; color: #334155; } QTableWidget::item { padding: 8px; } QTableWidget::item:selected { background: #e0f2fe; color: #0f172a; } QHeaderView::section { background: #f8fafc; border: none; border-bottom: 1px solid #e2e8f0; padding: 8px; color: #64748b; font-weight: bold; }")
        header = self.tabela.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.itemSelectionChanged.connect(self.selecionar_lancamento)
        coluna_lista.addWidget(self.tabela)
        conteudo.addLayout(coluna_lista, stretch=3)

        painel = QFrame()
        painel.setObjectName("PainelPagamento")
        painel.setFixedWidth(320)
        painel.setStyleSheet("""
            QFrame#PainelPagamento { background: white; border: 1px solid #e2e8f0; border-radius: 10px; }
            QLabel { color: #334155; font-size: 12px; font-weight: 500; border: none; background: transparent; }
            QLineEdit, QComboBox { background: white; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; min-height: 18px; }
            QLineEdit:focus, QComboBox:focus { border-color: #0284c7; }
            QComboBox QAbstractItemView { background: white; color: #0f172a; selection-background-color: #0284c7; }
        """)
        form = QVBoxLayout(painel)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(10)
        titulo_form = QLabel("Registrar pagamento")
        titulo_form.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        form.addWidget(titulo_form)
        self.lbl_consulta = QLabel("Selecione uma consulta na tabela.")
        self.lbl_consulta.setWordWrap(True)
        self.lbl_consulta.setStyleSheet("color: #64748b; font-size: 12px;")
        form.addWidget(self.lbl_consulta)
        form.addWidget(QLabel("Valor da consulta (R$):"))
        self.input_valor = QLineEdit()
        self.input_valor.setPlaceholderText("Ex: 150,00")
        form.addWidget(self.input_valor)
        form.addWidget(QLabel("Valor recebido (R$):"))
        self.input_recebido = QLineEdit()
        self.input_recebido.setPlaceholderText("Ex: 150,00")
        form.addWidget(self.input_recebido)
        form.addWidget(QLabel("Status do pagamento:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Pendente", "Parcial", "Pago", "Isento"])
        form.addWidget(self.combo_status)
        form.addWidget(QLabel("Forma de pagamento:"))
        self.combo_forma = QComboBox()
        self.combo_forma.addItems(["Não informado", "Pix", "Dinheiro", "Cartão", "Transferência", "Convênio"])
        form.addWidget(self.combo_forma)
        form.addWidget(QLabel("Observação:"))
        self.input_observacao = QLineEdit()
        form.addWidget(self.input_observacao)
        form.addStretch()
        self.btn_salvar = QPushButton("Salvar pagamento")
        self.btn_salvar.setStyleSheet("QPushButton { background: #0284c7; color: white; border: none; border-radius: 6px; padding: 11px; font-weight: bold; } QPushButton:hover { background: #0369a1; }")
        self.btn_salvar.clicked.connect(self.salvar_pagamento)
        form.addWidget(self.btn_salvar)
        conteudo.addWidget(painel)
        layout.addLayout(conteudo, stretch=1)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

    def _criar_card(self, titulo, valor, fundo, cor):
        card = QFrame()
        card.setFixedSize(210, 86)
        card.setStyleSheet("QFrame { background: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
        box = QVBoxLayout(card)
        box.setContentsMargins(14, 12, 14, 12)
        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet("color: #64748b; font-size: 12px;")
        lbl_valor = QLabel(valor)
        lbl_valor.setObjectName("valor")
        lbl_valor.setStyleSheet(f"background: {fundo}; color: {cor}; font-size: 20px; font-weight: bold; border-radius: 5px; padding: 2px 6px;")
        box.addWidget(lbl_titulo)
        box.addWidget(lbl_valor)
        return card

    @staticmethod
    def _moeda(valor):
        return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _numero(texto):
        texto = (texto or "0").strip().replace("R$", "").replace(".", "").replace(",", ".")
        try:
            return float(Decimal(texto))
        except (InvalidOperation, ValueError):
            return None

    def _definir_card(self, card, valor):
        card.findChild(QLabel, "valor").setText(valor)

    def carregar_dados(self):
        self.registros = []
        if not self.db.supabase:
            self.lbl_status.setText("Conecte-se ao Supabase para usar o Financeiro.")
            return
        try:
            cid = int(self.db.consultorio_id)
            agenda = self.db.supabase.table("agenda").select(
                "data, horario, paciente, procedimento, status"
            ).eq("consultorio_id", cid).eq("tipo_bloco", "principal").execute().data or []
            pagamentos_resp = self.db.supabase.table("pagamentos_consultas").select("*").eq("consultorio_id", cid).execute()
            pagamentos = pagamentos_resp.data or []
            por_consulta = {(p["agenda_data"], p["agenda_horario"]): p for p in pagamentos}
            for consulta in agenda:
                pagamento = por_consulta.get((consulta["data"], consulta["horario"]), {})
                self.registros.append({
                    **consulta,
                    **pagamento,
                    "agenda_data": consulta["data"],
                    "agenda_horario": consulta["horario"],
                    "status_consulta": consulta.get("status") or "Agendada",
                    "status_pagamento": pagamento.get("status") or "Pendente",
                })
            self._renderizar_tabela()
            self.lbl_status.setText("")
        except Exception as e:
            self.tabela.setRowCount(0)
            self.lbl_status.setText("Financeiro ainda não está configurado. Execute a consulta SQL indicada para ativá-lo.")
            print(f"Erro ao carregar financeiro: {e}")

    def _renderizar_tabela(self):
        # A tabela pode ter muitas consultas; desenhar somente ao final evita travadas visuais.
        self.tabela.setUpdatesEnabled(False)
        self.tabela.setRowCount(0)
        recebido_mes = pendente = 0.0
        mes_atual = QDate.currentDate().toString("MM/yyyy")
        for linha, registro in enumerate(sorted(self.registros, key=lambda r: (r["agenda_data"], r["agenda_horario"]), reverse=True)):
            valor = float(registro.get("valor") or 0)
            recebido = float(registro.get("valor_recebido") or 0)
            status = registro.get("status_pagamento") or "Pendente"
            if registro["agenda_data"].endswith(mes_atual):
                if status == "Pago":
                    recebido_mes += recebido
                pendente += max(valor - recebido, 0)
            self.tabela.insertRow(linha)
            data_consulta = QDate.fromString(registro["agenda_data"], "dd/MM/yyyy")
            atrasado = data_consulta.isValid() and data_consulta < QDate.currentDate() and status in ("Pendente", "Parcial")
            texto_status = "Pendente atrasado" if atrasado and status == "Pendente" else status
            valores = [registro["agenda_data"], registro.get("paciente", ""), registro.get("procedimento", ""), self._moeda(valor), self._moeda(recebido), texto_status]
            for coluna, texto in enumerate(valores):
                item = QTableWidgetItem(str(texto))
                if coluna == 0:
                    item.setData(Qt.ItemDataRole.UserRole, registro)
                if coluna == 5:
                    if status == "Pago":
                        item.setBackground(QColor("#dcfce7"))
                        item.setForeground(QColor("#15803d"))
                    elif atrasado:
                        item.setBackground(QColor("#fee2e2"))
                        item.setForeground(QColor("#b91c1c"))
                    elif status in ("Pendente", "Parcial"):
                        item.setBackground(QColor("#fef3c7"))
                        item.setForeground(QColor("#b45309"))
                    elif status == "Isento":
                        item.setBackground(QColor("#e0f2fe"))
                        item.setForeground(QColor("#0369a1"))
                self.tabela.setItem(linha, coluna, item)
        self._definir_card(self.card_recebido, self._moeda(recebido_mes))
        self._definir_card(self.card_pendente, self._moeda(pendente))
        self._definir_card(self.card_consultas, str(len(self.registros)))
        self.tabela.setUpdatesEnabled(True)

    def selecionar_lancamento(self):
        item = self.tabela.currentItem()
        if not item:
            return
        registro = self.tabela.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        self.registro_selecionado = registro
        self.lbl_consulta.setText(f"{registro.get('paciente', '')}\n{registro['agenda_data']} às {registro['agenda_horario']}")
        self.input_valor.setText(f"{float(registro.get('valor') or 0):.2f}".replace(".", ","))
        self.input_recebido.setText(f"{float(registro.get('valor_recebido') or 0):.2f}".replace(".", ","))
        self.combo_status.setCurrentText(registro.get("status_pagamento") or "Pendente")
        self.combo_forma.setCurrentText(registro.get("forma_pagamento") or "Não informado")
        self.input_observacao.setText(registro.get("observacao") or "")

    def salvar_pagamento(self):
        if not iniciar_operacao(self.btn_salvar, "Salvando pagamento..."):
            return

        if not self.registro_selecionado:
            finalizar_operacao(self.btn_salvar)
            QMessageBox.warning(self, "Selecione uma consulta", "Selecione uma consulta realizada na tabela primeiro.")
            return
        valor = self._numero(self.input_valor.text())
        recebido = self._numero(self.input_recebido.text())
        if valor is None or recebido is None or valor < 0 or recebido < 0:
            finalizar_operacao(self.btn_salvar)
            QMessageBox.warning(self, "Valor inválido", "Informe valores válidos, por exemplo: 150,00.")
            return
        try:
            cid = int(self.db.consultorio_id)
            registro = self.registro_selecionado
            payload = {
                "consultorio_id": cid, "agenda_data": registro["agenda_data"], "agenda_horario": registro["agenda_horario"],
                "paciente": registro.get("paciente", ""), "procedimento": registro.get("procedimento", ""),
                "valor": valor, "valor_recebido": recebido, "status": self.combo_status.currentText(),
                "forma_pagamento": self.combo_forma.currentText(), "observacao": self.input_observacao.text().strip(),
            }
            tabela = self.db.supabase.table("pagamentos_consultas")
            existente = tabela.select("id").eq("consultorio_id", cid).eq("agenda_data", registro["agenda_data"]).eq("agenda_horario", registro["agenda_horario"]).execute()
            if existente.data:
                tabela.update(payload).eq("id", existente.data[0]["id"]).execute()
                acao_auditoria = "UPDATE"
            else:
                tabela.insert(payload).execute()
                acao_auditoria = "INSERT"
            if hasattr(self.db, "registrar_evento_auditoria"):
                self.db.registrar_evento_auditoria(
                    acao_auditoria,
                    "pagamentos_consultas",
                    f"{registro['agenda_data']}:{registro['agenda_horario']}",
                    {"status_pagamento": self.combo_status.currentText()},
                )
            self.carregar_dados()
            self.lbl_status.setText("Pagamento salvo com sucesso.")
        except Exception as e:
            registrar_falha("salvar pagamento", e)
            QMessageBox.critical(self, "Pagamento não salvo", mensagem_erro_usuario("salvar o pagamento"))
        finally:
            finalizar_operacao(self.btn_salvar)
