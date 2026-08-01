import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page

    readonly property bool wideLayout: width >= 1000
    property int pendingDeleteId: 0
    property string pendingDeleteName: ""
    property string requestedFolder: ""

    function openEditor(patientId) {
        patientsController.selecionar(patientId)
        if (!wideLayout)
            editorDrawer.open()
    }

    function newPatient() {
        patientsController.novo()
        if (!wideLayout)
            editorDrawer.open()
    }

    function newPatientInFolder(folderName) {
        patientsController.novoNaPasta(folderName || "Geral")
        if (!wideLayout)
            editorDrawer.open()
    }

    function openFolder(folderName) {
        requestedFolder = folderName || "Geral"
        patientsController.definirPasta(requestedFolder)
        const position = patientsController.pastas.indexOf(requestedFolder)
        if (position >= 0)
            folderFilter.currentIndex = position
    }

    Component.onCompleted: {
        patientsController.novo()
        patientsController.carregar()
    }

    Connections {
        target: patientsController
        function onFeedback(kind, message) {
            feedbackLabel.text = message
            feedbackBar.color = kind === "success" ? "#e8f7ef"
                               : kind === "warning" ? "#fff7df"
                               : "#fff0f0"
            feedbackLabel.color = kind === "success" ? "#137548"
                                  : kind === "warning" ? "#8a5b00"
                                  : "#b42318"
            feedbackPopup.open()
        }
        function onEstadoAlterado() {
            if (!page.requestedFolder)
                return
            const position = patientsController.pastas.indexOf(
                page.requestedFolder)
            if (position >= 0 && folderFilter.currentIndex !== position)
                folderFilter.currentIndex = position
        }
        function onFichaVisualizacaoPronta(_title) {
            clinicalRecordDialog.open()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            AppTextField {
                Layout.fillWidth: true
                placeholderText: "Buscar por nome, CPF, RG ou telefone"
                onTextEdited: patientsController.definirBusca(text)
            }

            AppComboBox {
                id: folderFilter
                Layout.preferredWidth: page.width < 900 ? 170 : 220
                model: patientsController.pastas
                onCurrentTextChanged: patientsController.definirPasta(currentText)
            }

            AppButton {
                text: "Novo paciente"
                highlighted: true
                onClicked: page.newPatient()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 12
                color: "#ffffff"
                border.width: 1
                border.color: "#d9e3ef"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 45
                        color: "#f6f9fc"
                        radius: 12

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 8

                            Label {
                                Layout.preferredWidth: 52
                                text: "ID"
                                color: "#52647c"
                                font.weight: Font.DemiBold
                                font.pixelSize: 12
                            }
                            Label {
                                Layout.fillWidth: true
                                text: "Nome"
                                color: "#52647c"
                                font.weight: Font.DemiBold
                                font.pixelSize: 12
                            }
                            Label {
                                Layout.preferredWidth: page.width < 820 ? 130 : 180
                                text: "Telefone"
                                color: "#52647c"
                                font.weight: Font.DemiBold
                                font.pixelSize: 12
                            }
                            Label {
                                visible: page.width >= 850
                                Layout.preferredWidth: 150
                                text: "Convênio"
                                color: "#52647c"
                                font.weight: Font.DemiBold
                                font.pixelSize: 12
                            }
                            Label {
                                visible: page.width >= 700
                                Layout.preferredWidth: 130
                                text: "Pasta"
                                color: "#52647c"
                                font.weight: Font.DemiBold
                                font.pixelSize: 12
                            }
                        }
                    }

                    SmoothListView {
                        id: patientList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: patientsController.model
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {}

                        delegate: Rectangle {
                            id: row
                            required property int patientId
                            required property string name
                            required property string phone
                            required property string insurance
                            required property string folder

                            width: patientList.width
                            height: 46
                            color: mouse.containsMouse ? "#edf7ff" : "#ffffff"
                            border.width: 1
                            border.color: "#e4ebf3"

                            Behavior on color { ColorAnimation { duration: 100 } }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14
                                spacing: 8

                                Label {
                                    Layout.preferredWidth: 52
                                    text: row.patientId
                                    color: "#334155"
                                    font.pixelSize: 12
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: row.name
                                    color: "#14213a"
                                    font.pixelSize: 13
                                    font.weight: Font.Medium
                                    elide: Text.ElideRight
                                }
                                Label {
                                    Layout.preferredWidth: page.width < 820 ? 130 : 180
                                    text: row.phone
                                    color: "#475569"
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                                Label {
                                    visible: page.width >= 850
                                    Layout.preferredWidth: 150
                                    text: row.insurance
                                    color: "#475569"
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                                Label {
                                    visible: page.width >= 700
                                    Layout.preferredWidth: 130
                                    text: row.folder
                                    color: "#0877b1"
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: mouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: page.openEditor(row.patientId)
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: !patientsController.ocupado && patientsController.total === 0
                            text: "Nenhum paciente encontrado"
                            color: "#708198"
                            font.pixelSize: 14
                        }
                    }

                    BusyIndicator {
                        Layout.alignment: Qt.AlignHCenter
                        visible: patientsController.ocupado
                        running: visible
                    }

                    Label {
                        Layout.leftMargin: 14
                        Layout.bottomMargin: 10
                        text: patientsController.total + (patientsController.total === 1 ? " paciente" : " pacientes")
                        color: "#64748b"
                        font.pixelSize: 11
                    }
                }
            }

            Rectangle {
                visible: page.wideLayout
                Layout.fillHeight: true
                Layout.preferredWidth: 410
                radius: 12
                color: "#ffffff"
                border.width: 1
                border.color: "#d9e3ef"

                PatientForm {
                    anchors.fill: parent
                    anchors.margins: 18
                    controller: patientsController
                    onDeleteRequested: function(patientId, patientName) {
                        page.pendingDeleteId = patientId
                        page.pendingDeleteName = patientName
                        deleteDialog.open()
                    }
                }
            }
        }
    }

    Drawer {
        id: editorDrawer
        edge: Qt.RightEdge
        width: Math.min(page.width - 40, 520)
        height: page.height
        modal: true

        background: Rectangle { color: "#ffffff" }

        PatientForm {
            anchors.fill: parent
            anchors.margins: 20
            controller: patientsController
            onDeleteRequested: function(patientId, patientName) {
                page.pendingDeleteId = patientId
                page.pendingDeleteName = patientName
                deleteDialog.open()
            }
        }
    }

    Dialog {
        id: deleteDialog
        anchors.centerIn: parent
        modal: true
        title: "Excluir paciente"
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: patientsController.excluir(page.pendingDeleteId)

        Label {
            width: 340
            wrapMode: Text.WordWrap
            text: "Deseja remover " + page.pendingDeleteName
                  + " da lista? O histórico clínico será preservado."
            color: "#334155"
        }
    }

    Dialog {
        id: clinicalRecordDialog
        anchors.centerIn: parent
        width: Math.min(680, page.width - 40)
        height: Math.min(650, page.height - 40)
        contentWidth: Math.max(0, width - leftPadding - rightPadding)
        contentHeight: Math.max(300, height - 120)
        modal: true
        title: patientsController.fichaVisualizacaoTitulo
        standardButtons: Dialog.Close

        contentItem: ColumnLayout {
            spacing: 12

            Label {
                Layout.fillWidth: true
                text: "Dados registrados no atendimento"
                color: "#64748b"
                font.pixelSize: 12
            }

            SmoothScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    Repeater {
                        model: patientsController.fichaVisualizacaoDetalhes

                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: modelData.secao ? 38
                                                   : Math.max(58, valueLabel.implicitHeight + 36)
                            radius: 8
                            color: modelData.secao ? "#eaf6fd" : "#f8fafc"
                            border.width: modelData.secao ? 0 : 1
                            border.color: "#d9e3ef"

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 4

                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    color: modelData.secao ? "#0369a1" : "#334155"
                                    font.weight: Font.DemiBold
                                    font.pixelSize: modelData.secao ? 13 : 11
                                    wrapMode: Text.WordWrap
                                }
                                Label {
                                    id: valueLabel
                                    visible: !modelData.secao
                                    Layout.fillWidth: true
                                    text: modelData.valor
                                    color: "#0f172a"
                                    font.pixelSize: 13
                                    wrapMode: Text.WordWrap
                                    textFormat: Text.PlainText
                                }
                            }
                        }
                    }

                    Rectangle {
                        visible: patientsController.fichaVisualizacaoDetalhes.length === 0
                        Layout.fillWidth: true
                        Layout.preferredHeight: 54
                        radius: 8
                        color: "#f8fafc"
                        border.width: 1
                        border.color: "#d9e3ef"

                        Label {
                            anchors.centerIn: parent
                            text: "Esta ficha não possui campos preenchidos."
                            color: "#64748b"
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#d9e3ef"
            }

            RowLayout {
                Layout.fillWidth: true

                Label {
                    Layout.fillWidth: true
                    text: "Anexos"
                    color: "#0f172a"
                    font.weight: Font.DemiBold
                }
                Label {
                    text: patientsController.fichaVisualizacaoAnexos.length
                          + " arquivo(s)"
                    color: "#64748b"
                    font.pixelSize: 11
                }
            }

            Label {
                visible: patientsController.fichaVisualizacaoAnexos.length === 0
                Layout.fillWidth: true
                text: "Nenhuma foto ou PDF foi anexado a esta ficha."
                color: "#64748b"
                font.pixelSize: 12
            }

            SmoothListView {
                id: patientAttachmentList
                visible: patientsController.fichaVisualizacaoAnexos.length > 0
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(contentHeight, 132)
                clip: true
                spacing: 6
                model: patientsController.fichaVisualizacaoAnexos
                ScrollBar.vertical: ScrollBar {}

                delegate: Rectangle {
                    required property int index
                    required property var modelData
                    width: patientAttachmentList.width
                    height: 56
                    radius: 8
                    color: patientAttachmentMouse.containsMouse
                           ? "#eef7fd" : "#f8fafc"
                    border.width: 1
                    border.color: patientAttachmentMouse.containsMouse
                                  ? "#7cc4ec" : "#d9e3ef"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 9

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
                            color: "#0f172a"
                            elide: Text.ElideMiddle
                        }
                        AppButton {
                            text: patientsController.ocupado
                                  ? "Abrindo..." : "Abrir"
                            compact: true
                            enabled: !patientsController.ocupado
                            onClicked: patientsController.abrirAnexoFicha(index)
                        }
                    }

                    MouseArea {
                        id: patientAttachmentMouse
                        anchors.fill: parent
                        anchors.rightMargin: 90
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onDoubleClicked: patientsController.abrirAnexoFicha(index)
                    }
                }
            }
        }
    }

    Popup {
        id: feedbackPopup
        x: Math.max(16, page.width - width - 16)
        y: 16
        width: Math.min(400, page.width - 32)
        height: 54
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        Timer {
            interval: 3200
            running: feedbackPopup.opened
            onTriggered: feedbackPopup.close()
        }

        background: Rectangle {
            id: feedbackBar
            radius: 9
            border.width: 1
            border.color: Qt.darker(color, 1.08)
        }

        Label {
            id: feedbackLabel
            anchors.fill: parent
            anchors.margins: 14
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }
    }
}

