import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

SmoothScrollView {
    id: root

    property var controller
    property var patientId: null
    signal deleteRequested(int patientId, string patientName)

    clip: true
    contentWidth: availableWidth

    function choose(combo, value) {
        const index = combo.find(value)
        combo.currentIndex = index >= 0 ? index : 0
    }

    function digits(value, limit) {
        return String(value || "").replace(/\D/g, "").slice(0, limit)
    }

    function formatPhone(value) {
        const number = digits(value, 11)
        if (number.length <= 2)
            return number
        if (number.length <= 6)
            return "(" + number.slice(0, 2) + ") " + number.slice(2)
        if (number.length <= 10)
            return "(" + number.slice(0, 2) + ") " + number.slice(2, 6)
                   + "-" + number.slice(6)
        return "(" + number.slice(0, 2) + ") " + number.slice(2, 7)
               + "-" + number.slice(7)
    }

    function formatDate(value) {
        const number = digits(value, 8)
        if (number.length <= 2)
            return number
        if (number.length <= 4)
            return number.slice(0, 2) + "/" + number.slice(2)
        return number.slice(0, 2) + "/" + number.slice(2, 4)
               + "/" + number.slice(4)
    }

    function formatCpf(value) {
        const number = digits(value, 11)
        if (number.length <= 3)
            return number
        if (number.length <= 6)
            return number.slice(0, 3) + "." + number.slice(3)
        if (number.length <= 9)
            return number.slice(0, 3) + "." + number.slice(3, 6)
                   + "." + number.slice(6)
        return number.slice(0, 3) + "." + number.slice(3, 6)
               + "." + number.slice(6, 9) + "-" + number.slice(9)
    }

    function normalizeRg(value) {
        return String(value || "").toUpperCase()
                     .replace(/[^0-9A-Z]/g, "").slice(0, 14)
    }

    function formatRg(value) {
        const normalized = normalizeRg(value)
        if (!/^\d+$/.test(normalized) || normalized.length > 9)
            return normalized
        if (normalized.length <= 2)
            return normalized
        if (normalized.length <= 5)
            return normalized.slice(0, 2) + "." + normalized.slice(2)
        if (normalized.length <= 8)
            return normalized.slice(0, 2) + "." + normalized.slice(2, 5)
                   + "." + normalized.slice(5)
        return normalized.slice(0, 2) + "." + normalized.slice(2, 5)
               + "." + normalized.slice(5, 8) + "-" + normalized.slice(8)
    }

    function formatField(field, formatter) {
        const formatted = formatter(field.text)
        if (field.text !== formatted) {
            field.text = formatted
            field.cursorPosition = field.text.length
        }
    }

    function populate(patient) {
        patientId = patient.id || null
        nameField.text = patient.nome || ""
        phoneField.text = formatPhone(patient.telefone)
        birthField.text = formatDate(patient.nascimento)
        insuranceField.text = patient.convenio || "PARTICULAR"
        choose(folderField, patient.pasta || "Geral")
        choose(sexField, patient.sexo || "Não informado")
        cpfField.text = formatCpf(patient.cpf)
        rgField.text = formatRg(patient.rg)
        choose(civilField, patient.estado_civil || "Não informado")
        professionField.text = patient.profissao || ""
        addressField.text = patient.endereco || ""
        complaintField.text = patient.queixa || ""
        remindersField.checked = Boolean(patient.lembretes_whatsapp_ativos)
    }

    Connections {
        target: root.controller
        function onSelecaoAlterada() {
            root.populate(root.controller.pacienteSelecionado)
        }
    }

    ColumnLayout {
        width: root.availableWidth
        spacing: 13

        Label {
            text: root.patientId ? "Editar paciente" : "Novo paciente"
            color: "#0f172a"
            font.pixelSize: 19
            font.weight: Font.DemiBold
        }

        Label {
            Layout.fillWidth: true
            text: root.controller.podeVerDadosClinicos
                  ? "Dados cadastrais e informações do prontuário."
                  : "Dados necessários para identificação e agendamento."
            color: "#64748b"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        Label { text: "Nome completo *"; color: "#334155"; font.pixelSize: 12 }
        AppTextField {
            id: nameField
            Layout.fillWidth: true
            placeholderText: "Nome completo"
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width >= 520 ? 2 : 1
            columnSpacing: 12
            rowSpacing: 8

            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "Telefone / celular"; color: "#334155"; font.pixelSize: 12 }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    AppTextField {
                        id: phoneField
                        Layout.fillWidth: true
                        placeholderText: "Ex.: 11999998888"
                        inputMethodHints: Qt.ImhDigitsOnly
                        maximumLength: 15
                        onTextEdited: root.formatField(phoneField, root.formatPhone)
                    }

                    AppButton {
                        text: "WhatsApp"
                        variant: "success"
                        compact: true
                        enabled: !root.controller.ocupado
                                 && root.digits(phoneField.text, 11).length >= 10
                        ToolTip.visible: hovered
                        ToolTip.text: "Abrir conversa com a mensagem configurada"
                        onClicked: root.controller.abrirWhatsApp(
                            phoneField.text,
                            nameField.text
                        )
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "Data de nascimento"; color: "#334155"; font.pixelSize: 12 }
                AppTextField {
                    id: birthField
                    Layout.fillWidth: true
                    placeholderText: "dd/mm/aaaa"
                    maximumLength: 10
                    inputMethodHints: Qt.ImhDigitsOnly
                    onTextEdited: root.formatField(birthField, root.formatDate)
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "Convênio / plano"; color: "#334155"; font.pixelSize: 12 }
                AppTextField {
                    id: insuranceField
                    Layout.fillWidth: true
                    text: "PARTICULAR"
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "Pasta"; color: "#334155"; font.pixelSize: 12 }
                AppComboBox {
                    id: folderField
                    Layout.fillWidth: true
                    model: root.controller.pastas.slice(1)
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "Sexo biológico"; color: "#334155"; font.pixelSize: 12 }
                AppComboBox {
                    id: sexField
                    Layout.fillWidth: true
                    model: ["Não informado", "Masculino", "Feminino", "Outro"]
                }
            }

            ColumnLayout {
                visible: root.controller.podeVerDadosClinicos
                Layout.fillWidth: true
                Label { text: "CPF"; color: "#334155"; font.pixelSize: 12 }
                AppTextField {
                    id: cpfField
                    Layout.fillWidth: true
                    placeholderText: "000.000.000-00"
                    maximumLength: 14
                    inputMethodHints: Qt.ImhDigitsOnly
                    onTextEdited: root.formatField(cpfField, root.formatCpf)
                }
            }

            ColumnLayout {
                visible: root.controller.podeVerDadosClinicos
                Layout.fillWidth: true
                Label { text: "RG"; color: "#334155"; font.pixelSize: 12 }
                AppTextField {
                    id: rgField
                    Layout.fillWidth: true
                    placeholderText: "Ex.: 12.345.678-9"
                    maximumLength: 17
                    onTextEdited: root.formatField(rgField, root.formatRg)
                }
            }

            ColumnLayout {
                visible: root.controller.podeVerDadosClinicos
                Layout.fillWidth: true
                Label { text: "Estado civil"; color: "#334155"; font.pixelSize: 12 }
                AppComboBox {
                    id: civilField
                    Layout.fillWidth: true
                    model: [
                        "Não informado",
                        "Solteiro(a)",
                        "Casado(a)",
                        "União estável",
                        "Separado(a)",
                        "Divorciado(a)",
                        "Viúvo(a)",
                        "Outro"
                    ]
                }
            }

            ColumnLayout {
                visible: root.controller.podeVerDadosClinicos
                Layout.fillWidth: true
                Label { text: "Profissão"; color: "#334155"; font.pixelSize: 12 }
                AppTextField { id: professionField; Layout.fillWidth: true }
            }
        }

        ColumnLayout {
            visible: root.controller.podeVerDadosClinicos
            Layout.fillWidth: true
            Label { text: "Endereço residencial"; color: "#334155"; font.pixelSize: 12 }
            AppTextField { id: addressField; Layout.fillWidth: true }
        }

        ColumnLayout {
            visible: root.controller.podeVerDadosClinicos
            Layout.fillWidth: true
            Label { text: "Queixa principal inicial"; color: "#334155"; font.pixelSize: 12 }
            AppTextArea {
                id: complaintField
                Layout.fillWidth: true
                Layout.preferredHeight: 82
                wrapMode: TextEdit.Wrap
                placeholderText: "Motivo inicial do atendimento"
            }
        }

        AppCheckBox {
            id: remindersField
            visible: root.controller.podeVerDadosClinicos
            text: "Permitir lembretes automáticos"
        }

        Rectangle {
            visible: root.controller.podeVerDadosClinicos
                     && Boolean(root.patientId)
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#d9e3ef"
        }

        RowLayout {
            visible: root.controller.podeVerDadosClinicos
                     && Boolean(root.patientId)
            Layout.fillWidth: true

            Label {
                Layout.fillWidth: true
                text: "Histórico de fichas"
                color: "#0f172a"
                font.pixelSize: 14
                font.weight: Font.DemiBold
            }
            Label {
                text: root.controller.totalHistorico + " registro(s)"
                color: "#64748b"
                font.pixelSize: 11
            }
        }

        Label {
            visible: root.controller.podeVerDadosClinicos
                     && Boolean(root.patientId)
                     && root.controller.totalHistorico === 0
            Layout.fillWidth: true
            text: "Nenhuma ficha clínica registrada para este paciente."
            color: "#64748b"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        SmoothListView {
            id: clinicalHistory
            visible: root.controller.podeVerDadosClinicos
                     && Boolean(root.patientId)
                     && root.controller.totalHistorico > 0
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, 210)
            clip: true
            spacing: 7
            model: root.controller.historicoModel
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            delegate: Rectangle {
                id: historyRow
                required property int recordId
                required property string modelName
                required property string appointmentDate
                required property int attachmentCount

                width: clinicalHistory.width
                height: 66
                radius: 8
                color: historyMouse.containsMouse ? "#eef7fd" : "#f8fafc"
                border.width: 1
                border.color: historyMouse.containsMouse ? "#7cc4ec" : "#d9e3ef"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 8

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3

                        Label {
                            Layout.fillWidth: true
                            text: historyRow.modelName
                            color: "#0f172a"
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }
                        Label {
                            text: historyRow.appointmentDate
                                  + (historyRow.attachmentCount > 0
                                     ? " · " + historyRow.attachmentCount
                                       + " anexo(s)" : "")
                            color: "#64748b"
                            font.pixelSize: 11
                        }
                    }

                    AppButton {
                        text: "Visualizar"
                        compact: true
                        onClicked: root.controller.visualizarFicha(
                            historyRow.recordId)
                    }
                }

                MouseArea {
                    id: historyMouse
                    anchors.fill: parent
                    anchors.rightMargin: 100
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onDoubleClicked: root.controller.visualizarFicha(
                        historyRow.recordId)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            AppButton {
                Layout.fillWidth: true
                text: "Limpar"
                onClicked: root.controller.novo()
            }
            AppButton {
                Layout.fillWidth: true
                text: root.controller.ocupado ? "Salvando..." : "Salvar paciente"
                enabled: !root.controller.ocupado
                highlighted: true
                onClicked: root.controller.salvar({
                    "id": root.patientId,
                    "nome": nameField.text,
                    "telefone": phoneField.text,
                    "nascimento": birthField.text,
                    "convenio": insuranceField.text,
                    "pasta": folderField.currentText || "Geral",
                    "sexo": sexField.currentText,
                    "cpf": cpfField.text,
                    "rg": rgField.text,
                    "estado_civil": civilField.currentText,
                    "profissao": professionField.text,
                    "endereco": addressField.text,
                    "queixa": complaintField.text,
                    "lembretes_whatsapp_ativos": remindersField.checked
                })
            }
        }

        AppButton {
            visible: Boolean(root.patientId)
            Layout.fillWidth: true
            text: "Excluir paciente"
            variant: "danger"
            onClicked: root.deleteRequested(Number(root.patientId), nameField.text)
        }
    }
}

