import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page
    objectName: "financeiroPage"
    readonly property bool compactLayout: width < 900

    function updateAutomaticStatus() {
        let calculated = financeiroController.calcularStatus(
            valueField.text, receivedField.text, statusBox.currentText
        )
        let index = statusBox.find(calculated)
        if (index >= 0)
            statusBox.currentIndex = index
    }

    Component.onCompleted: financeiroController.carregar()

    Connections {
        target: financeiroController

        function onFormularioCarregado(data) {
            consultationLabel.text = data.consulta || ""
            valueField.text = data.valor || "0,00"
            receivedField.text = data.recebido || "0,00"
            let statusIndex = statusBox.find(data.status || "Pendente")
            statusBox.currentIndex = statusIndex >= 0 ? statusIndex : 0
            let paymentIndex = paymentBox.find(data.forma || "Não informado")
            paymentBox.currentIndex = paymentIndex >= 0 ? paymentIndex : 0
            noteField.text = data.observacao || ""
            page.updateAutomaticStatus()
        }

        function onFeedback(kind, message) {
            feedbackText.text = message
            feedbackBackground.color = kind === "success" ? "#e8f7ef"
                                     : kind === "warning" ? "#fff7df" : "#fff0f0"
            feedbackText.color = kind === "success" ? "#137548"
                               : kind === "warning" ? "#8a5b00" : "#b42318"
            feedbackPopup.open()
        }
    }

    SmoothScrollView {
        id: pageScroll
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: pageScroll.availableWidth
            spacing: 14

        GridLayout {
            Layout.fillWidth: true
            columns: page.compactLayout ? 1 : 3
            rowSpacing: 12
            columnSpacing: 12

            Repeater {
                model: [
                    {
                        title: "Recebido no mês",
                        value: financeiroController.recebidoMes,
                        background: "#dcfce7",
                        color: "#15803d"
                    },
                    {
                        title: "A receber no mês",
                        value: financeiroController.aReceber,
                        background: "#fef3c7",
                        color: "#b45309"
                    },
                    {
                        title: "Consultas na agenda",
                        value: String(financeiroController.consultasAgenda),
                        background: "#e0f2fe",
                        color: "#0369a1"
                    }
                ]

                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: page.compactLayout
                                           ? pageScroll.availableWidth
                                           : (pageScroll.availableWidth - 24) / 3
                    Layout.preferredHeight: 84
                    radius: 11
                    color: "#ffffff"
                    border.color: "#d9e3ef"

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        Label {
                            text: modelData.title
                            color: "#64748b"
                            font.pixelSize: 12
                        }
                        Rectangle {
                            width: parent.width
                            height: 36
                            radius: 6
                            color: modelData.background
                            Label {
                                anchors.left: parent.left
                                anchors.leftMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.value
                                color: modelData.color
                                font.pixelSize: 20
                                font.weight: Font.Bold
                            }
                        }
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: page.compactLayout ? 1 : 2
            rowSpacing: 10
            columnSpacing: 10

            AppTextField {
                Layout.fillWidth: true
                placeholderText: "Buscar por paciente, procedimento ou data"
                onTextEdited: financeiroController.definirBusca(text)
            }
            AppComboBox {
                Layout.fillWidth: page.compactLayout
                Layout.preferredWidth: page.compactLayout ? -1 : 190
                model: financeiroController.statusFiltros
                onCurrentTextChanged: financeiroController.definirFiltroStatus(currentText)
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: page.compactLayout ? 1 : 2
            rowSpacing: 16
            columnSpacing: 16

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: page.compactLayout
                                        ? 320
                                        : Math.max(420, page.height - 210)
                radius: 12
                color: "#ffffff"
                border.color: "#d9e3ef"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        color: "#f6f9fc"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            Label {
                                Layout.preferredWidth: 85
                                text: "Data"
                                color: "#52657f"
                                font.weight: Font.DemiBold
                            }
                            Label {
                                Layout.fillWidth: true
                                text: "Paciente / procedimento"
                                color: "#52657f"
                                font.weight: Font.DemiBold
                            }
                            Label {
                                Layout.preferredWidth: 100
                                text: "Valor"
                                color: "#52657f"
                                font.weight: Font.DemiBold
                            }
                            Label {
                                Layout.preferredWidth: 120
                                text: "Situação"
                                color: "#52657f"
                                font.weight: Font.DemiBold
                            }
                        }
                    }

                    SmoothListView {
                        id: financeList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: financeiroController.model
                        ScrollBar.vertical: ScrollBar {}

                        delegate: Rectangle {
                            required property string appointmentDate
                            required property string appointmentTime
                            required property string patientName
                            required property string procedureName
                            required property string consultationValue
                            required property string receivedValue
                            required property string paymentStatus
                            required property bool overdue

                            width: financeList.width
                            height: 62
                            color: rowMouse.containsMouse ? "#eef7fd" : "#ffffff"
                            border.width: 1
                            border.color: "#e2eaf3"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 8

                                Column {
                                    Layout.preferredWidth: 85
                                    Label { text: appointmentDate; color: "#0f172a" }
                                    Label {
                                        text: appointmentTime
                                        color: "#64748b"
                                        font.pixelSize: 11
                                    }
                                }
                                Column {
                                    Layout.fillWidth: true
                                    Label {
                                        width: parent.width
                                        text: patientName
                                        elide: Text.ElideRight
                                        color: "#0f172a"
                                        font.weight: Font.DemiBold
                                    }
                                    Label {
                                        width: parent.width
                                        text: procedureName
                                        elide: Text.ElideRight
                                        color: "#64748b"
                                        font.pixelSize: 11
                                    }
                                }
                                Column {
                                    Layout.preferredWidth: 100
                                    Label { text: consultationValue; color: "#334155" }
                                    Label {
                                        text: "Recebido: " + receivedValue
                                        color: "#64748b"
                                        font.pixelSize: 10
                                    }
                                }
                                Rectangle {
                                    Layout.preferredWidth: 120
                                    Layout.preferredHeight: 30
                                    radius: 6
                                    color: paymentStatus === "Pago" ? "#dcfce7"
                                         : paymentStatus === "Isento" ? "#e0f2fe"
                                         : overdue ? "#fee2e2" : "#fef3c7"
                                    Label {
                                        anchors.centerIn: parent
                                        text: paymentStatus
                                        color: paymentStatus === "Pago" ? "#15803d"
                                             : paymentStatus === "Isento" ? "#0369a1"
                                             : overdue ? "#b91c1c" : "#b45309"
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                    }
                                }
                            }

                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: financeiroController.selecionar(
                                    appointmentDate, appointmentTime
                                )
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: financeiroController.total === 0
                            text: "Nenhuma consulta encontrada."
                            color: "#64748b"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: page.compactLayout
                Layout.preferredWidth: page.compactLayout ? -1 : 320
                Layout.preferredHeight: page.compactLayout
                                        ? 500
                                        : Math.max(420, page.height - 210)
                radius: 12
                color: "#ffffff"
                border.color: "#d9e3ef"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8

                    Label {
                        text: "Registrar pagamento"
                        color: "#0f172a"
                        font.pixelSize: 17
                        font.weight: Font.Bold
                    }
                    Label {
                        id: consultationLabel
                        Layout.fillWidth: true
                        text: "Selecione uma consulta na lista."
                        color: "#64748b"
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                    Label { text: "Valor da consulta (R$)" }
                    AppTextField {
                        id: valueField
                        Layout.fillWidth: true
                        placeholderText: "Ex.: 150,00"
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                        onTextEdited: page.updateAutomaticStatus()
                    }
                    Label { text: "Valor recebido (R$)" }
                    AppTextField {
                        id: receivedField
                        Layout.fillWidth: true
                        placeholderText: "Ex.: 150,00"
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                        onTextEdited: page.updateAutomaticStatus()
                    }
                    Label { text: "Situação do pagamento" }
                    AppComboBox {
                        id: statusBox
                        Layout.fillWidth: true
                        model: ["Pendente", "Parcial", "Pago", "Isento"]
                    }
                    Label { text: "Forma de pagamento" }
                    AppComboBox {
                        id: paymentBox
                        Layout.fillWidth: true
                        model: [
                            "Não informado", "Pix", "Dinheiro", "Cartão",
                            "Transferência", "Convênio"
                        ]
                    }
                    Label { text: "Observação" }
                    AppTextArea {
                        id: noteField
                        Layout.fillWidth: true
                        Layout.preferredHeight: 75
                        wrapMode: TextEdit.Wrap
                    }
                    Item { Layout.fillHeight: true }
                    BusyIndicator {
                        Layout.alignment: Qt.AlignHCenter
                        running: financeiroController.ocupado
                        visible: running
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: "Salvar pagamento"
                        highlighted: true
                        enabled: !financeiroController.ocupado
                                 && financeiroController.temSelecao
                        onClicked: financeiroController.salvar(
                            valueField.text,
                            receivedField.text,
                            statusBox.currentText,
                            paymentBox.currentText,
                            noteField.text
                        )
                    }
                }
            }
        }
        }
    }

    Popup {
        id: feedbackPopup
        anchors.centerIn: parent
        width: Math.min(440, page.width - 40)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            id: feedbackBackground
            radius: 10
            border.color: "#d9e3ef"
        }
        contentItem: Label {
            id: feedbackText
            padding: 16
            wrapMode: Text.WordWrap
        }
    }
}

