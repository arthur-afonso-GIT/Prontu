import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page

    property var answers: ({})
    readonly property bool compact: width < 980

    function answer(fieldId) {
        return answers[fieldId] === undefined ? "" : answers[fieldId]
    }

    function setAnswer(fieldId, value) {
        let copy = Object.assign({}, answers)
        copy[fieldId] = value
        answers = copy
    }

    function syncSelectors() {
        for (let i = 0; i < patientBox.count; ++i) {
            if (Number(patientBox.valueAt(i)) === fichasController.pacienteSelecionadoId) {
                patientBox.currentIndex = i
                break
            }
        }
        let modelIndex = modelBox.find(fichasController.modeloSelecionado)
        if (modelIndex >= 0)
            modelBox.currentIndex = modelIndex
    }

    Component.onCompleted: fichasController.carregar()

    Connections {
        target: fichasController

        function onFormularioCarregado(values) {
            page.answers = Object.assign({}, values)
            page.syncSelectors()
        }

        function onEstadoAlterado() {
            page.syncSelectors()
        }

        function onFeedback(kind, message) {
            feedbackText.text = message
            feedbackBox.color = kind === "success" ? "#e8f7ef"
                              : kind === "warning" ? "#fff7df" : "#fff0f0"
            feedbackText.color = kind === "success" ? "#137548"
                               : kind === "warning" ? "#8a5b00" : "#b42318"
            feedbackPopup.open()
        }

        function onVisualizacaoAnexosPronta(title) {
            attachmentsDialog.title = "Anexos — " + title
            attachmentsDialog.open()
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 16

        Rectangle {
            Layout.preferredWidth: page.compact ? 300 : 330
            Layout.fillHeight: true
            radius: 12
            color: "#ffffff"
            border.color: "#d9e3ef"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                Label {
                    text: "Atendimento clínico"
                    color: "#0f172a"
                    font.pixelSize: 17
                    font.weight: Font.Bold
                }

                Label { text: "Paciente"; color: "#475569"; font.pixelSize: 12 }
                AppComboBox {
                    id: patientBox
                    Layout.fillWidth: true
                    model: fichasController.pacientes
                    textRole: "nome"
                    valueRole: "id"
                    enabled: !fichasController.editando
                    onActivated: fichasController.selecionarPaciente(Number(currentValue))
                }

                Label { text: "Modelo de ficha"; color: "#475569"; font.pixelSize: 12 }
                AppComboBox {
                    id: modelBox
                    Layout.fillWidth: true
                    model: fichasController.nomesModelos
                    enabled: !fichasController.editando
                    onActivated: fichasController.selecionarModelo(currentText)
                }

                AppButton {
                    Layout.fillWidth: true
                    text: "Nova ficha"
                    enabled: !fichasController.ocupado
                    onClicked: fichasController.novaFicha()
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 7
                    AppButton {
                        Layout.fillWidth: true
                        text: "Criar modelo"
                        onClicked: modelBuilder.begin(false, "")
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: "Editar modelo"
                        enabled: modelBox.currentText.toLowerCase().indexOf("padrão") < 0
                        onClicked: modelBuilder.begin(true, modelBox.currentText)
                    }
                }

                AppButton {
                    Layout.fillWidth: true
                    text: "Importar modelo Word ou PDF"
                    enabled: !fichasController.ocupado
                    onClicked: fichasController.importarModeloDocumento()
                }

                AppButton {
                    Layout.fillWidth: true
                    text: "Excluir modelo"
                    variant: "danger"
                    enabled: modelBox.currentText.toLowerCase().indexOf("padrão") < 0
                    onClicked: deleteModelDialog.open()
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: "#d9e3ef"
                }

                Label {
                    text: "Histórico do paciente"
                    color: "#0f172a"
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }

                Label {
                    visible: fichasController.totalHistorico === 0
                    text: patientBox.currentIndex < 0
                          ? "Selecione um paciente."
                          : "Nenhuma ficha registrada."
                    color: "#64748b"
                    font.pixelSize: 12
                }

                ListView {
                    id: historyList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 7
                    model: fichasController.historicoModel

                    ScrollBar.vertical: ScrollBar {}

                    delegate: Rectangle {
                        required property int recordId
                        required property string modelName
                        required property string appointmentDate
                        required property int attachmentCount

                        width: historyList.width
                        height: attachmentCount > 0 ? 92 : 70
                        radius: 8
                        color: historyMouse.containsMouse ? "#eef7fd" : "#f8fafc"
                        border.color: historyMouse.containsMouse ? "#7cc4ec" : "#d9e3ef"

                        Column {
                            anchors.left: parent.left
                            anchors.right: historyActions.left
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 11
                            anchors.rightMargin: 8
                            spacing: 4
                            Label {
                                width: parent.width
                                text: modelName
                                elide: Text.ElideRight
                                color: "#0f172a"
                                font.weight: Font.DemiBold
                            }
                            Label {
                                text: appointmentDate
                                      + (attachmentCount > 0
                                         ? " · " + attachmentCount + " anexo(s)" : "")
                                color: "#64748b"
                                font.pixelSize: 11
                            }
                        }

                        Column {
                            id: historyActions
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 5

                            AppButton {
                                text: "Abrir ficha"
                                onClicked: fichasController.abrirFicha(recordId)
                            }
                            AppButton {
                                visible: attachmentCount > 0
                                text: "Ver anexos"
                                variant: "ghost"
                                onClicked: fichasController.visualizarAnexosFicha(recordId)
                            }
                        }

                        MouseArea {
                            id: historyMouse
                            anchors.fill: parent
                            anchors.rightMargin: historyActions.width + 12
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onDoubleClicked: fichasController.abrirFicha(recordId)
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 12
            color: "#ffffff"
            border.color: "#d9e3ef"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: fichasController.editando
                              ? "Editando ficha existente"
                              : fichasController.modeloSelecionado
                        color: "#0f172a"
                        font.pixelSize: 18
                        font.weight: Font.Bold
                    }
                    Label {
                        visible: fichasController.editando
                        text: "Paciente e modelo preservados"
                        color: "#137548"
                        font.pixelSize: 12
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    Column {
                        width: parent.width
                        spacing: 13

                        Repeater {
                            model: fichasController.camposModelo
                            ClinicalField {
                                required property var modelData
                                width: parent.width
                                fieldData: modelData
                                fieldValue: page.answer(modelData.id || "")
                                onEdited: function(value) {
                                    page.setAnswer(modelData.id, value)
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 7

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            Layout.fillWidth: true
                            text: fichasController.anexos.length > 0
                                  ? "Anexos do atendimento · "
                                    + fichasController.anexos.length
                                  : "Anexos do atendimento"
                            color: "#0f172a"
                            font.weight: Font.DemiBold
                        }
                        AppButton {
                            text: "Adicionar foto ou PDF"
                            enabled: !fichasController.ocupado
                            onClicked: fichasController.escolherAnexos()
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: fichasController.anexos.length > 0
                              ? "Clique em um arquivo para visualizá-lo. "
                                + "Novos arquivos serão enviados ao salvar a ficha."
                              : "Adicione fotos ou PDFs; os arquivos serão enviados "
                                + "junto com a ficha."
                        color: "#64748b"
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }

                    ListView {
                        id: attachmentList
                        Layout.fillWidth: true
                        Layout.preferredHeight: fichasController.anexos.length > 0 ? 54 : 0
                        visible: height > 0
                        orientation: ListView.Horizontal
                        spacing: 7
                        clip: true
                        model: fichasController.anexos

                        delegate: Rectangle {
                            required property int index
                            required property var modelData
                            width: Math.min(210, attachmentList.width)
                            height: 48
                            radius: 7
                            color: attachmentMouse.containsMouse ? "#eef7fd" : "#f8fafc"
                            border.color: "#cbd8e6"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 7
                                Label {
                                    text: modelData.nome.toLowerCase().endsWith(".pdf")
                                          ? "PDF" : "IMG"
                                    color: "#0788c9"
                                    font.weight: Font.Bold
                                    font.pixelSize: 10
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.nome
                                    elide: Text.ElideMiddle
                                    color: "#334155"
                                }
                                AppButton {
                                    text: "Remover"
                                    compact: true
                                    variant: "danger"
                                    ToolTip.visible: hovered
                                    ToolTip.text: modelData.local
                                                  ? "Retirar arquivo selecionado"
                                                  : "Remover anexo ao salvar"
                                    onClicked: fichasController.removerAnexo(index)
                                }
                            }
                            MouseArea {
                                id: attachmentMouse
                                anchors.fill: parent
                                anchors.rightMargin: 92
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: fichasController.abrirAnexo(index)
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: "* Campo obrigatório"
                        color: "#64748b"
                        font.pixelSize: 11
                    }
                    BusyIndicator {
                        running: fichasController.ocupado
                        visible: running
                    }
                    AppButton {
                        text: fichasController.editando
                              ? "Salvar alterações" : "Salvar ficha"
                        highlighted: true
                        enabled: !fichasController.ocupado
                                 && patientBox.currentIndex >= 0
                        onClicked: fichasController.salvar(
                            Number(patientBox.currentValue),
                            modelBox.currentText,
                            page.answers
                        )
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    AppButton {
                        Layout.fillWidth: true
                        text: "Exportar Word"
                        enabled: !fichasController.ocupado
                                 && fichasController.pacienteSelecionadoId > 0
                        onClicked: fichasController.exportarWord(page.answers)
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: "Exportar PDF"
                        enabled: !fichasController.ocupado
                                 && fichasController.pacienteSelecionadoId > 0
                        onClicked: fichasController.exportarPdf(page.answers)
                    }
                }
            }
        }
    }

    Popup {
        id: feedbackPopup
        anchors.centerIn: parent
        width: Math.min(440, page.width - 40)
        modal: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            id: feedbackBox
            radius: 10
            border.color: "#d9e3ef"
        }

        contentItem: Label {
            id: feedbackText
            padding: 16
            wrapMode: Text.WordWrap
        }
    }

    ModelBuilderDialog {
        id: modelBuilder
    }

    Dialog {
        id: attachmentsDialog
        anchors.centerIn: parent
        width: Math.min(540, page.width - 40)
        height: Math.min(430, page.height - 40)
        modal: true
        standardButtons: Dialog.Close

        contentItem: ColumnLayout {
            spacing: 10

            Label {
                Layout.fillWidth: true
                text: "Selecione um arquivo para abrir."
                color: "#64748b"
                font.pixelSize: 12
            }

            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 7
                model: fichasController.anexosVisualizacao
                ScrollBar.vertical: ScrollBar {}

                delegate: Rectangle {
                    required property int index
                    required property var modelData
                    width: ListView.view.width
                    height: 58
                    radius: 8
                    color: attachmentPreviewMouse.containsMouse
                           ? "#eef7fd" : "#f8fafc"
                    border.color: attachmentPreviewMouse.containsMouse
                                  ? "#7cc4ec" : "#d9e3ef"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 10

                        Rectangle {
                            Layout.preferredWidth: 38
                            Layout.preferredHeight: 38
                            radius: 9
                            color: "#dff2fc"
                            Label {
                                anchors.centerIn: parent
                                text: modelData.nome.toLowerCase().endsWith(".pdf")
                                      ? "PDF" : "IMG"
                                color: "#0369a1"
                                font.pixelSize: 10
                                font.weight: Font.Bold
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: modelData.nome
                            elide: Text.ElideMiddle
                            color: "#0f172a"
                            font.weight: Font.DemiBold
                        }
                        AppButton {
                            text: "Abrir"
                            onClicked: fichasController.abrirAnexoVisualizacao(index)
                        }
                    }

                    MouseArea {
                        id: attachmentPreviewMouse
                        anchors.fill: parent
                        anchors.rightMargin: 82
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onDoubleClicked:
                            fichasController.abrirAnexoVisualizacao(index)
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteModelDialog
        anchors.centerIn: parent
        width: Math.min(430, page.width - 40)
        contentWidth: Math.max(0, width - leftPadding - rightPadding)
        modal: true
        title: "Excluir modelo"
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: fichasController.excluirModelo(modelBox.currentText)

        contentItem: Label {
            wrapMode: Text.WordWrap
            text: "Excluir o modelo “" + modelBox.currentText
                  + "”? As fichas já preenchidas não serão apagadas."
        }
    }
}

