from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_entrada_oficial_qml_e_arquivos_principais_existem():
    assert (ROOT / "main.py").is_file()
    assert not (ROOT / "qml_main.py").exists()
    assert (ROOT / "ui" / "qml_controller.py").is_file()
    assert (ROOT / "ui" / "qml" / "Main.qml").is_file()
    assert (ROOT / "ui" / "qml" / "Login.qml").is_file()
    assert (ROOT / "ui" / "qml_login_controller.py").is_file()
    assert (ROOT / "services" / "auth_service.py").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "AppButton.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "AppTextField.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "AppTextArea.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "AppComboBox.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "AppCheckBox.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "AppRadioButton.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "AppSpinBox.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "AgendaWeekView.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "AgendaMonthView.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "NavButton.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "PatientForm.qml").is_file()
    assert (ROOT / "ui" / "qml" / "pages" / "HomePage.qml").is_file()
    assert (ROOT / "ui" / "qml_home_controller.py").is_file()
    assert (ROOT / "services" / "home_service.py").is_file()
    assert (ROOT / "ui" / "qml" / "pages" / "PatientsPage.qml").is_file()
    assert (ROOT / "ui" / "qml" / "pages" / "AgendaPage.qml").is_file()
    assert (ROOT / "ui" / "qml_agenda_controller.py").is_file()
    assert (ROOT / "ui" / "qml" / "pages" / "FichasPage.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "ClinicalField.qml").is_file()
    assert (ROOT / "ui" / "qml" / "components" / "ModelBuilderDialog.qml").is_file()
    assert (ROOT / "ui" / "qml_fichas_controller.py").is_file()
    assert (ROOT / "ui" / "qml" / "pages" / "FinanceiroPage.qml").is_file()
    assert (ROOT / "ui" / "qml_financeiro_controller.py").is_file()
    assert (ROOT / "ui" / "qml" / "pages" / "EquipePage.qml").is_file()
    assert (ROOT / "ui" / "qml_equipe_controller.py").is_file()
    assert (ROOT / "ui" / "qml" / "pages" / "ConfiguracoesPage.qml").is_file()
    assert (ROOT / "ui" / "qml_configuracoes_controller.py").is_file()


def test_main_e_a_unica_entrada_visual_do_aplicativo():
    conteudo = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "QQmlApplicationEngine" in conteudo
    assert '"Main.qml"' in conteudo
    assert '"Login.qml"' in conteudo
    assert "LoginDialog" not in conteudo
    assert "MainWindow" not in conteudo


def test_paleta_qml_mantem_texto_legivel_em_hover_e_selecao():
    for arquivo in ("Main.qml", "Login.qml"):
        conteudo = (ROOT / "ui" / "qml" / arquivo).read_text(
            encoding="utf-8"
        )
        assert 'palette.highlight: "#d9effb"' in conteudo
        assert 'palette.highlightedText: "#075985"' in conteudo


def test_campos_qml_usam_componentes_visuais_padronizados():
    components = ROOT / "ui" / "qml" / "components"
    field = (components / "AppTextField.qml").read_text(encoding="utf-8")
    area = (components / "AppTextArea.qml").read_text(encoding="utf-8")

    for content in (field, area):
        assert 'return "#0788c9"' in content
        assert 'return "#7cc4ec"' in content
        assert "control.activeFocus ? 2 : 1" in content

    consumers = [
        ROOT / "ui" / "qml" / "Login.qml",
        ROOT / "ui" / "qml" / "components" / "PatientForm.qml",
        ROOT / "ui" / "qml" / "components" / "ClinicalField.qml",
        ROOT / "ui" / "qml" / "pages" / "AgendaPage.qml",
        ROOT / "ui" / "qml" / "pages" / "ConfiguracoesPage.qml",
        ROOT / "ui" / "qml" / "pages" / "EquipePage.qml",
        ROOT / "ui" / "qml" / "pages" / "FinanceiroPage.qml",
        ROOT / "ui" / "qml" / "pages" / "PatientsPage.qml",
    ]
    for path in consumers:
        content = path.read_text(encoding="utf-8")
        assert "TextField {" not in content.replace("AppTextField {", "")
        assert "TextArea {" not in content.replace("AppTextArea {", "")


def test_seletores_e_senhas_qml_usam_componentes_padronizados():
    components = ROOT / "ui" / "qml" / "components"
    combo = (components / "AppComboBox.qml").read_text(encoding="utf-8")
    check = (components / "AppCheckBox.qml").read_text(encoding="utf-8")
    radio = (components / "AppRadioButton.qml").read_text(encoding="utf-8")
    spin = (components / "AppSpinBox.qml").read_text(encoding="utf-8")
    password = (components / "AppTextField.qml").read_text(encoding="utf-8")

    assert 'palette.highlightedText: "#075f92"' in combo
    assert 'text: "✓"' in check
    assert 'color: "#0b8fd3"' in radio
    assert "editable: true" in spin
    assert "property bool revealable: false" in password
    assert 'control.passwordVisible ? "Ocultar" : "Mostrar"' in password

    consumers = [
        ROOT / "ui" / "qml" / "Login.qml",
        ROOT / "ui" / "qml" / "components" / "PatientForm.qml",
        ROOT / "ui" / "qml" / "components" / "ClinicalField.qml",
        ROOT / "ui" / "qml" / "components" / "ModelBuilderDialog.qml",
        ROOT / "ui" / "qml" / "pages" / "AgendaPage.qml",
        ROOT / "ui" / "qml" / "pages" / "ConfiguracoesPage.qml",
        ROOT / "ui" / "qml" / "pages" / "EquipePage.qml",
        ROOT / "ui" / "qml" / "pages" / "FinanceiroPage.qml",
        ROOT / "ui" / "qml" / "pages" / "FichasPage.qml",
        ROOT / "ui" / "qml" / "pages" / "PatientsPage.qml",
    ]
    for path in consumers:
        content = path.read_text(encoding="utf-8")
        assert "ComboBox {" not in content.replace("AppComboBox {", "")
        assert "CheckBox {" not in content.replace("AppCheckBox {", "")
        assert "RadioButton {" not in content.replace("AppRadioButton {", "")
        assert "SpinBox {" not in content.replace("AppSpinBox {", "")


def test_arquivos_qml_estao_em_utf8_sem_texto_corrompido():
    qml_root = ROOT / "ui" / "qml"
    sinais_de_codificacao_incorreta = (
        "Ã£", "Ã§", "Ã©", "Ã³", "Ãª", "Ãµ", "Ã¡", "Ã­", "Ãº",
        "Ã‰", "Ãš", "Â·", "â€", "ðŸ", "ï¿½", "\ufffd",
    )

    for path in qml_root.rglob("*.qml"):
        content = path.read_text(encoding="utf-8", errors="strict")
        for sinal in sinais_de_codificacao_incorreta:
            assert sinal not in content, (
                f"Texto com codificação incorreta em {path}: {sinal!r}"
            )


def test_fontes_distribuidas_estao_em_utf8_sem_texto_corrompido():
    sinais_de_codificacao_incorreta = (
        "Ã£", "Ã§", "Ã©", "Ã³", "Ãª", "Ãµ", "Ã¡", "Ã­", "Ãº",
        "Ã‰", "Ãš", "Â·", "â€", "ðŸ", "ï¿½", "\ufffd",
    )
    extensoes = {".py", ".qml", ".md", ".iss", ".ps1", ".spec"}
    raizes = (
        ROOT / "main.py",
        ROOT / "database",
        ROOT / "services",
        ROOT / "ui",
        ROOT / "installer",
        ROOT / "scripts",
        ROOT / "README.md",
    )

    arquivos = []
    for raiz in raizes:
        if raiz.is_file():
            arquivos.append(raiz)
        elif raiz.is_dir():
            arquivos.extend(
                caminho
                for caminho in raiz.rglob("*")
                if caminho.is_file() and caminho.suffix.lower() in extensoes
            )

    for caminho in arquivos:
        conteudo = caminho.read_text(encoding="utf-8", errors="strict")
        for sinal in sinais_de_codificacao_incorreta:
            assert sinal not in conteudo, (
                f"Texto com codificação incorreta em {caminho}: {sinal!r}"
            )


def test_entrada_oficial_usa_login_qml():
    conteudo = (ROOT / "main.py").read_text(encoding="utf-8")
    assert '"Login.qml"' in conteudo
    assert "LoginDialog" not in conteudo


def test_empacotamento_usa_entrada_oficial_e_inclui_recursos_qml():
    conteudo = (ROOT / "installer" / "Prontu.spec").read_text(encoding="utf-8")
    assert 'ROOT / "main.py"' in conteudo
    assert 'ROOT / "ui" / "qml"' in conteudo
    assert "styles.qss" not in conteudo


def test_interface_qt_widgets_legada_foi_removida():
    caminhos_antigos = (
        ROOT / "ui" / "main_window.py",
        ROOT / "ui" / "login_dialog.py",
        ROOT / "ui" / "styles.qss",
    )
    for caminho in caminhos_antigos:
        assert not caminho.exists()
    assert not list((ROOT / "ui" / "screens").glob("*.py"))


def test_qml_declara_responsividade_e_controle_de_permissao():
    conteudo = (ROOT / "ui" / "qml" / "Main.qml").read_text(encoding="utf-8")
    assert "compactNavigation" in conteudo
    assert "window.controller.podeGerenciarEquipe" in conteudo
    assert "window.controller.podeVerFichas" in conteudo
    assert '"pages/HomePage.qml"' in conteudo
    assert '"pages/PatientsPage.qml"' in conteudo
    assert '"pages/AgendaPage.qml"' in conteudo
    assert '"pages/FichasPage.qml"' in conteudo
    assert '"pages/FinanceiroPage.qml"' in conteudo
    assert '"pages/EquipePage.qml"' in conteudo
    assert '"pages/ConfiguracoesPage.qml"' in conteudo


def test_qml_possui_fallback_durante_encerramento_dos_controladores():
    principal = (ROOT / "ui" / "qml" / "Main.qml").read_text(
        encoding="utf-8"
    )
    configuracoes = (
        ROOT / "ui" / "qml" / "pages" / "ConfiguracoesPage.qml"
    ).read_text(encoding="utf-8")

    assert "fallbackAppController" in principal
    assert 'typeof appController !== "undefined"' in principal
    assert "appController." not in principal
    assert "fallbackController" in configuracoes
    assert 'typeof configuracoesController !== "undefined"' in configuracoes
    assert "configuracoesController." not in configuracoes


def test_confirmacao_de_exclusao_de_modelo_tem_largura_estavel():
    conteudo = (
        ROOT / "ui" / "qml" / "pages" / "FichasPage.qml"
    ).read_text(encoding="utf-8")

    trecho = conteudo.split("id: deleteModelDialog", 1)[1]
    assert "contentWidth: Math.max(0, width - leftPadding - rightPadding)" in trecho
    assert "contentItem: Label" in trecho


def test_formulario_qml_oferece_atalho_manual_para_whatsapp():
    formulario = (
        ROOT / "ui" / "qml" / "components" / "PatientForm.qml"
    ).read_text(encoding="utf-8")
    botao = (
        ROOT / "ui" / "qml" / "components" / "AppButton.qml"
    ).read_text(encoding="utf-8")

    assert 'text: "WhatsApp"' in formulario
    assert "root.controller.abrirWhatsApp" in formulario
    assert 'variant === "success"' in botao


def test_tela_de_fichas_qml_oferece_exportacao_word_e_pdf():
    conteudo = (
        ROOT / "ui" / "qml" / "pages" / "FichasPage.qml"
    ).read_text(encoding="utf-8")

    assert 'text: "Exportar Word"' in conteudo
    assert 'text: "Exportar PDF"' in conteudo
    assert "fichasController.exportarWord(page.answers)" in conteudo
    assert "fichasController.exportarPdf(page.answers)" in conteudo


def test_historico_qml_oferece_abertura_da_ficha_e_dos_anexos():
    conteudo = (
        ROOT / "ui" / "qml" / "pages" / "FichasPage.qml"
    ).read_text(encoding="utf-8")

    assert 'text: "Abrir ficha"' in conteudo
    assert 'text: "Ver anexos"' in conteudo
    assert "fichasController.visualizarAnexosFicha(recordId)" in conteudo
    assert "fichasController.abrirAnexoVisualizacao(index)" in conteudo


def test_agendamento_de_retorno_qml_oferece_calendario_e_digitacao_manual():
    agenda = (
        ROOT / "ui" / "qml" / "pages" / "AgendaPage.qml"
    ).read_text(encoding="utf-8")
    calendario = (
        ROOT / "ui" / "qml" / "components" / "DatePicker.qml"
    ).read_text(encoding="utf-8")

    assert "DatePicker {" in agenda
    assert "returnCalendar.showDate" in agenda
    assert "onEditingFinished" in agenda
    assert "MonthGrid {" in calendario
    assert 'locale: Qt.locale("pt_BR")' in calendario
