import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    objectName: "configuracoesPage"

    QtObject {
        id: fallbackController

        readonly property string papelTexto: ""
        readonly property bool ocupado: false
        readonly property bool proprietario: false
        readonly property bool automacaoWhatsApp: false
        readonly property string resumoLembretes: ""
        readonly property string franquiaLembretes: ""
        readonly property var lembretes: []
        readonly property var auditoria: []

        function carregar() {}
        function salvarPerfil(_nome) {}
        function abrirDiagnostico() {}
        function salvarMensagens(_manual, _lembrete) {}
        function carregarLembretes() {}
        function escolherPastaBackup() { return "" }
        function executarBackup(_pasta, _senha, _confirmacao, _retencao, _anexos) {}
        function escolherArquivoRestauracao() {}
        function filtrarAuditoria(_filtro) {}
        function carregarAuditoria() {}
        function restaurarBackup(_arquivo, _senha, _substituir, _confirmacao) {}
        function desativarDispositivo() {}
    }

    readonly property var controller:
        (typeof configuracoesController !== "undefined" && configuracoesController)
        ? configuracoesController : fallbackController

    property string planoNome: "Prontu"
    property string assinaturaStatus: ""
    property string limiteUsuarios: ""
    property string arquivoRestauracao: ""
    property string statusBackup: "Último backup: nunca executado"

    Component.onCompleted: page.controller.carregar()

    Connections {
        target: page.controller
        ignoreUnknownSignals: true

        function onDadosCarregados(dados) {
            page.planoNome = dados.plano || "Prontu"
            page.assinaturaStatus = dados.status || ""
            page.limiteUsuarios = dados.limite || ""
            nomeField.text = dados.nome || ""
            mensagemManual.text = dados.mensagem_manual || ""
            mensagemLembrete.text = dados.mensagem_lembrete || ""
            pastaBackup.text = dados.backup_dir || ""
            retencao.value = Number(dados.backup_retencao || 30)
            incluirAnexos.checked = Boolean(dados.backup_anexos)
            page.statusBackup = dados.backup_status || "Último backup: nunca executado"
        }

        function onFeedback(tipo, mensagem) {
            feedbackText.text = mensagem
            feedbackBox.color = tipo === "success" ? "#e8f7ef"
                              : tipo === "warning" ? "#fff7df" : "#fff0f0"
            feedbackText.color = tipo === "success" ? "#137548"
                               : tipo === "warning" ? "#8a5b00" : "#b42318"
            feedbackPopup.open()
        }

        function onArquivoRestauracaoSelecionado(caminho) {
            page.arquivoRestauracao = caminho
            restoreFile.text = caminho
            restoreDialog.open()
        }

        function onProgressoBackup(mensagem) {
            progressText.text = mensagem
        }

        function onSessaoDesativada() {
            Qt.quit()
        }
    }

    SmoothScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: Math.max(page.width, 760)
            spacing: 16

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 92
                radius: 12
                color: "#f0f9ff"
                border.color: "#bae6fd"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 14

                    Rectangle {
                        Layout.preferredWidth: 48
                        Layout.preferredHeight: 48
                        radius: 14
                        color: "#dbeafe"
                        Label {
                            anchors.centerIn: parent
                            text: "⚙"
                            color: "#0369a1"
                            font.pixelSize: 24
                        }
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 4
                        Label {
                            text: page.planoNome
                            color: "#0f172a"
                            font.pixelSize: 18
                            font.weight: Font.Bold
                        }
                        Label {
                            text: page.assinaturaStatus + " · " + page.limiteUsuarios
                            color: "#475569"
                            font.pixelSize: 12
                        }
                    }

                    Rectangle {
                        implicitWidth: roleLabel.implicitWidth + 26
                        implicitHeight: 32
                        radius: 16
                        color: "#ffffff"
                        border.color: "#bae6fd"
                        Label {
                            id: roleLabel
                            anchors.centerIn: parent
                            text: page.controller.papelTexto
                            color: "#0369a1"
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                        }
                    }

                    BusyIndicator {
                        running: page.controller.ocupado
                        visible: running
                    }

                    AppButton {
                        text: "Atualizar"
                        enabled: !page.controller.ocupado
                        onClicked: page.controller.carregar()
                    }
                }
            }

            TabBar {
                id: tabs
                Layout.fillWidth: true

                TabButton { text: "Perfil" }
                TabButton { text: "WhatsApp" }
                TabButton { text: "Backup" }
                TabButton {
                    text: "Auditoria"
                    visible: page.controller.proprietario
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(560, page.height - 190)
                currentIndex: tabs.currentIndex

                // Perfil
                Rectangle {
                    radius: 12
                    color: "#ffffff"
                    border.color: "#d9e3ef"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 22
                        spacing: 14

                        Label {
                            text: "Perfil de acesso"
                            color: "#0f172a"
                            font.pixelSize: 18
                            font.weight: Font.Bold
                        }
                        Label {
                            text: "Este nome identifica você dentro da clínica."
                            color: "#64748b"
                            font.pixelSize: 12
                        }
                        Label {
                            text: "Nome de exibição"
                            color: "#334155"
                            font.weight: Font.DemiBold
                        }
                        AppTextField {
                            id: nomeField
                            Layout.fillWidth: true
                            placeholderText: "Ex.: Dra. Laura Silva"
                            selectByMouse: true
                        }
                        AppButton {
                            text: "Salvar perfil"
                            enabled: !page.controller.ocupado
                            onClicked: page.controller.salvarPerfil(nomeField.text)
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: "#e2e8f0"
                        }

                        Label {
                            text: "Suporte e diagnóstico"
                            color: "#0f172a"
                            font.pixelSize: 16
                            font.weight: Font.Bold
                        }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "O diagnóstico contém apenas registros técnicos locais para ajudar a identificar falhas."
                            color: "#64748b"
                            font.pixelSize: 12
                        }
                        AppButton {
                            text: "Abrir pasta de diagnóstico"
                            onClicked: page.controller.abrirDiagnostico()
                        }

                        Item { Layout.fillHeight: true }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 94
                            radius: 10
                            color: "#fff7f7"
                            border.color: "#fecaca"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 15
                                Column {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Label {
                                        text: "Desativar este dispositivo"
                                        color: "#991b1b"
                                        font.weight: Font.Bold
                                    }
                                    Label {
                                        text: "Encerra a sessão somente neste computador."
                                        color: "#7f1d1d"
                                        font.pixelSize: 12
                                    }
                                }
                                AppButton {
                                    text: "Desativar"
                                    variant: "danger"
                                    onClicked: deactivateDialog.open()
                                }
                            }
                        }
                    }
                }

                // WhatsApp
                Rectangle {
                    radius: 12
                    color: "#ffffff"
                    border.color: "#d9e3ef"

                    SmoothScrollView {
                        anchors.fill: parent
                        anchors.margins: 20
                        clip: true

                        ColumnLayout {
                            width: Math.max(parent.width - 4, 680)
                            spacing: 12

                            Label {
                                text: "Mensagens do WhatsApp"
                                color: "#0f172a"
                                font.pixelSize: 18
                                font.weight: Font.Bold
                            }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: "Você pode usar {paciente}, {profissional}, {data}, {hora} e {procedimento}. O Prontu substitui esses campos automaticamente."
                                color: "#64748b"
                                font.pixelSize: 12
                            }
                            Label {
                                text: "Mensagem do botão Zap"
                                color: "#334155"
                                font.weight: Font.DemiBold
                            }
                            AppTextArea {
                                id: mensagemManual
                                Layout.fillWidth: true
                                Layout.preferredHeight: 110
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                placeholderText: "Mensagem enviada ao abrir o WhatsApp"
                            }
                            Label {
                                text: "Mensagem de lembrete de consulta"
                                color: "#334155"
                                font.weight: Font.DemiBold
                            }
                            AppTextArea {
                                id: mensagemLembrete
                                Layout.fillWidth: true
                                Layout.preferredHeight: 125
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                placeholderText: "Mensagem usada nos lembretes"
                            }
                            AppButton {
                                text: "Salvar mensagens"
                                enabled: !page.controller.ocupado
                                onClicked: page.controller.salvarMensagens(
                                               mensagemManual.text,
                                               mensagemLembrete.text)
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: "#e2e8f0"
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Column {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Label {
                                        text: "Acompanhamento dos lembretes"
                                        color: "#0f172a"
                                        font.pixelSize: 16
                                        font.weight: Font.Bold
                                    }
                                    Label {
                                        text: page.controller.automacaoWhatsApp
                                              ? page.controller.resumoLembretes
                                              : "Automação em preparação. O envio manual continua disponível."
                                        color: "#64748b"
                                        font.pixelSize: 12
                                    }
                                    Label {
                                        visible: page.controller.automacaoWhatsApp
                                        text: page.controller.franquiaLembretes
                                        color: "#0369a1"
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                    }
                                }
                                AppButton {
                                    visible: page.controller.automacaoWhatsApp
                                    text: "Atualizar envios"
                                    enabled: !page.controller.ocupado
                                    onClicked: page.controller.carregarLembretes()
                                }
                            }

                            SmoothListView {
                                id: remindersList
                                visible: page.controller.automacaoWhatsApp
                                Layout.fillWidth: true
                                Layout.preferredHeight: 220
                                clip: true
                                spacing: 7
                                model: page.controller.lembretes
                                ScrollBar.vertical: ScrollBar {}

                                delegate: Rectangle {
                                    required property var modelData
                                    width: remindersList.width
                                    height: 66
                                    radius: 8
                                    color: modelData.falhou ? "#fff7f7"
                                          : modelData.entregue ? "#f0fdf4" : "#f8fafc"
                                    border.color: modelData.falhou ? "#fecaca"
                                                : modelData.entregue ? "#bbf7d0" : "#e2e8f0"

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        Column {
                                            Layout.fillWidth: true
                                            spacing: 2
                                            Label {
                                                text: modelData.paciente + " · " + modelData.consulta
                                                color: "#0f172a"
                                                font.weight: Font.DemiBold
                                            }
                                            Label {
                                                text: modelData.procedimento
                                                color: "#64748b"
                                                font.pixelSize: 11
                                            }
                                        }
                                        Label {
                                            text: modelData.situacao
                                            color: modelData.falhou ? "#b42318"
                                                  : modelData.entregue ? "#137548" : "#475569"
                                            font.weight: Font.DemiBold
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Backup
                Rectangle {
                    radius: 12
                    color: "#ffffff"
                    border.color: "#d9e3ef"

                    SmoothScrollView {
                        anchors.fill: parent
                        anchors.margins: 20
                        clip: true

                        ColumnLayout {
                            width: Math.max(parent.width - 4, 680)
                            spacing: 12

                            Label {
                                text: "Backup local criptografado"
                                color: "#0f172a"
                                font.pixelSize: 18
                                font.weight: Font.Bold
                            }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: "Crie uma cópia protegida por senha dos dados desta clínica."
                                color: "#64748b"
                                font.pixelSize: 12
                            }
                            Label {
                                text: "Pasta de destino"
                                color: "#334155"
                                font.weight: Font.DemiBold
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                AppTextField {
                                    id: pastaBackup
                                    Layout.fillWidth: true
                                    selectByMouse: true
                                }
                                AppButton {
                                    text: "Escolher pasta"
                                    onClicked: {
                                        var caminho = page.controller.escolherPastaBackup()
                                        if (caminho)
                                            pastaBackup.text = caminho
                                    }
                                }
                            }
                            RowLayout {
                                spacing: 18
                                Label { text: "Retenção (dias)" }
                                AppSpinBox {
                                    id: retencao
                                    from: 1
                                    to: 3650
                                    value: 30
                                    editable: true
                                }
                                AppCheckBox {
                                    id: incluirAnexos
                                    text: "Incluir metadados dos anexos"
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: "Retenção é por quanto tempo os backups ficam guardados. Arquivos mais antigos que esse prazo são apagados automaticamente após um novo backup."
                                color: "#64748b"
                                font.pixelSize: 11
                            }
                            Label { text: "Senha de recuperação"; font.weight: Font.DemiBold }
                            AppTextField {
                                id: backupPassword
                                Layout.fillWidth: true
                                revealable: true
                                placeholderText: "Digite uma senha forte"
                            }
                            Label { text: "Confirmar senha"; font.weight: Font.DemiBold }
                            AppTextField {
                                id: backupPasswordConfirm
                                Layout.fillWidth: true
                                revealable: true
                                placeholderText: "Digite a mesma senha novamente"
                            }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: "Guarde esta senha: ela é necessária para restaurar o arquivo."
                                color: "#64748b"
                                font.pixelSize: 11
                            }
                            Label {
                                text: page.statusBackup
                                color: "#475569"
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                            Label {
                                id: progressText
                                visible: text.length > 0
                                color: "#0369a1"
                                font.pixelSize: 12
                            }
                            RowLayout {
                                spacing: 10
                                AppButton {
                                    text: "Executar backup agora"
                                    enabled: !page.controller.ocupado
                                    onClicked: page.controller.executarBackup(
                                                   pastaBackup.text,
                                                   backupPassword.text,
                                                   backupPasswordConfirm.text,
                                                   retencao.value,
                                                   incluirAnexos.checked)
                                }
                                AppButton {
                                    text: "Restaurar backup"
                                    enabled: !page.controller.ocupado
                                    onClicked: page.controller.escolherArquivoRestauracao()
                                }
                            }
                        }
                    }
                }

                // Auditoria
                Rectangle {
                    radius: 12
                    color: "#ffffff"
                    border.color: "#d9e3ef"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            Column {
                                Layout.fillWidth: true
                                spacing: 3
                                Label {
                                    text: "Histórico de auditoria"
                                    color: "#0f172a"
                                    font.pixelSize: 18
                                    font.weight: Font.Bold
                                }
                                Label {
                                    text: "Alterações importantes registradas na clínica."
                                    color: "#64748b"
                                    font.pixelSize: 12
                                }
                            }
                            AppComboBox {
                                id: auditFilter
                                textRole: "label"
                                valueRole: "value"
                                model: [
                                    { label: "Todas as áreas", value: "" },
                                    { label: "Pacientes", value: "pacientes" },
                                    { label: "Agenda", value: "agenda" },
                                    { label: "Fichas clínicas", value: "fichas_preenchidas" },
                                    { label: "Financeiro", value: "pagamentos_consultas" },
                                    { label: "Configurações", value: "configuracoes" },
                                    { label: "Backup", value: "backup" }
                                ]
                                onActivated: page.controller.filtrarAuditoria(
                                                 currentValue)
                            }
                            AppButton {
                                text: "Atualizar histórico"
                                enabled: !page.controller.ocupado
                                onClicked: page.controller.carregarAuditoria()
                            }
                        }

                        SmoothListView {
                            id: auditList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 7
                            model: page.controller.auditoria
                            ScrollBar.vertical: ScrollBar {}

                            delegate: Rectangle {
                                required property var modelData
                                width: auditList.width
                                height: 76
                                radius: 8
                                color: auditMouse.hovered ? "#f6fbff" : "#ffffff"
                                border.color: "#dce6f1"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 11
                                    Column {
                                        Layout.preferredWidth: 145
                                        Label {
                                            text: modelData.data
                                            color: "#475569"
                                            font.pixelSize: 11
                                        }
                                        Label {
                                            text: modelData.area
                                            color: "#0369a1"
                                            font.weight: Font.DemiBold
                                        }
                                    }
                                    Column {
                                        Layout.fillWidth: true
                                        Label {
                                            text: modelData.acao
                                            color: "#0f172a"
                                            font.weight: Font.DemiBold
                                        }
                                        Label {
                                            width: parent.width
                                            text: modelData.resumo
                                            color: "#64748b"
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                    }
                                    Column {
                                        Layout.preferredWidth: 230
                                        spacing: 2
                                        Label {
                                            text: "Responsável"
                                            color: "#64748b"
                                            font.pixelSize: 10
                                        }
                                        Label {
                                            width: parent.width
                                            text: modelData.responsavel
                                            color: "#0f172a"
                                            font.pixelSize: 12
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                                HoverHandler { id: auditMouse }
                            }

                            Label {
                                anchors.centerIn: parent
                                visible: auditList.count === 0
                                text: "Clique em “Atualizar histórico” para carregar os registros."
                                color: "#94a3b8"
                            }
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: feedbackPopup
        anchors.centerIn: Overlay.overlay
        width: Math.min(460, page.width - 40)
        modal: true
        padding: 0

        background: Rectangle {
            id: feedbackBox
            radius: 12
            border.color: "#d9e3ef"
        }

        contentItem: ColumnLayout {
            spacing: 14
            anchors.margins: 18
            Label {
                id: feedbackText
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            AppButton {
                Layout.alignment: Qt.AlignRight
                text: "OK"
                onClicked: feedbackPopup.close()
            }
        }
    }

    Dialog {
        id: restoreDialog
        anchors.centerIn: parent
        width: Math.min(570, page.width - 40)
        modal: true
        title: "Restaurar backup"
        standardButtons: Dialog.NoButton

        contentItem: ColumnLayout {
            spacing: 10
            Label { text: "Arquivo selecionado"; font.weight: Font.DemiBold }
            Label {
                id: restoreFile
                Layout.fillWidth: true
                elide: Text.ElideMiddle
                color: "#475569"
            }
            Label { text: "Senha de recuperação"; font.weight: Font.DemiBold }
            AppTextField {
                id: restorePassword
                Layout.fillWidth: true
                revealable: true
            }
            AppRadioButton {
                id: safeRestore
                checked: true
                text: "Adicionar apenas o que não existe"
            }
            AppRadioButton {
                id: replaceRestore
                text: "Substituir os dados atuais pelos dados do backup"
            }
            Label {
                visible: replaceRestore.checked
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "A substituição remove os dados atuais desta clínica antes de restaurar. Digite SUBSTITUIR abaixo para confirmar."
                color: "#b42318"
            }
            AppTextField {
                id: replaceConfirmation
                visible: replaceRestore.checked
                Layout.fillWidth: true
                placeholderText: "Digite SUBSTITUIR"
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: restoreDialog.close()
                }
                AppButton {
                    text: "Restaurar"
                    enabled: !page.controller.ocupado
                    onClicked: {
                        page.controller.restaurarBackup(
                            page.arquivoRestauracao,
                            restorePassword.text,
                            replaceRestore.checked,
                            replaceConfirmation.text)
                        restoreDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: deactivateDialog
        anchors.centerIn: parent
        width: Math.min(440, page.width - 40)
        modal: true
        title: "Desativar dispositivo"
        standardButtons: Dialog.NoButton

        contentItem: ColumnLayout {
            spacing: 14
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Deseja encerrar a sessão do Prontu neste computador?"
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: deactivateDialog.close()
                }
                AppButton {
                    text: "Desativar"
                    variant: "danger"
                    onClicked: {
                        deactivateDialog.close()
                        page.controller.desativarDispositivo()
                    }
                }
            }
        }
    }
}

