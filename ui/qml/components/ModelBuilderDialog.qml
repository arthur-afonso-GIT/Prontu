import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog

    property bool editingExisting: false
    property int editingIndex: -1

    modal: true
    width: Math.min(920, parent ? parent.width - 40 : 920)
    height: Math.min(680, parent ? parent.height - 40 : 680)
    anchors.centerIn: parent
    padding: 0
    closePolicy: Popup.NoAutoClose

    function begin(editExisting, selectedName) {
        editingExisting = editExisting
        editingIndex = -1
        modelName.text = editExisting ? selectedName : ""
        clearEditor()
        fichasController.iniciarConstrutor(editExisting)
        if (!editExisting || selectedName.toLowerCase().indexOf("padrão") < 0)
            open()
    }

    function clearEditor() {
        editingIndex = -1
        typeBox.currentIndex = 0
        labelField.clear()
        helpField.clear()
        optionsField.clear()
        unitField.clear()
        requiredCheck.checked = false
        todayCheck.checked = false
    }

    function editField(index, field) {
        editingIndex = index
        let typeIndex = typeBox.find(field.tipo || "texto_curto")
        typeBox.currentIndex = typeIndex >= 0 ? typeIndex : 0
        labelField.text = field.label || ""
        helpField.text = field.ajuda || field.placeholder || ""
        optionsField.text = (field.opcoes || []).join(", ")
        unitField.text = field.unidade || ""
        requiredCheck.checked = Boolean(field.obrigatorio)
        todayCheck.checked = Boolean(field.preencher_hoje)
    }

    function fieldPayload() {
        let payload = {
            "tipo": typeBox.currentValue,
            "label": labelField.text.trim(),
            "obrigatorio": requiredCheck.checked
        }
        if (helpField.text.trim().length > 0)
            payload.ajuda = helpField.text.trim()
        if (typeBox.currentValue === "multipla_escolha")
            payload.opcoes = optionsField.text.split(",").map(
                function(value) { return value.trim() }
            ).filter(function(value) { return value.length > 0 })
        if (typeBox.currentValue === "numero" && unitField.text.trim().length > 0)
            payload.unidade = unitField.text.trim()
        if (typeBox.currentValue === "data")
            payload.preencher_hoje = todayCheck.checked
        return payload
    }

    background: Rectangle {
        radius: 14
        color: "#ffffff"
        border.color: "#cbd8e6"
    }

    contentItem: ColumnLayout {
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 62
            color: "#f5f9fd"
            radius: 14

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 14
                Label {
                    Layout.fillWidth: true
                    text: dialog.editingExisting
                          ? "Editar modelo de ficha" : "Criar modelo de ficha"
                    color: "#0f172a"
                    font.pixelSize: 19
                    font.weight: Font.Bold
                }
                AppButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: {
                        fichasController.cancelarConstrutor()
                        dialog.close()
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 18
            spacing: 18

            Rectangle {
                Layout.preferredWidth: 310
                Layout.fillHeight: true
                radius: 10
                color: "#f8fafc"
                border.color: "#d9e3ef"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    Label {
                        text: dialog.editingIndex >= 0
                              ? "Editar campo" : "Adicionar campo"
                        font.weight: Font.Bold
                        color: "#0f172a"
                    }
                    AppComboBox {
                        id: typeBox
                        Layout.fillWidth: true
                        textRole: "label"
                        valueRole: "value"
                        model: [
                            { label: "Texto curto", value: "texto_curto" },
                            { label: "Texto longo", value: "texto_longo" },
                            { label: "Caixa de seleção", value: "checkbox" },
                            { label: "Número", value: "numero" },
                            { label: "Data", value: "data" },
                            { label: "Múltipla escolha", value: "multipla_escolha" },
                            { label: "Seção / título", value: "secao" }
                        ]
                    }
                    AppTextField {
                        id: labelField
                        Layout.fillWidth: true
                        placeholderText: typeBox.currentValue === "secao"
                                         ? "Título da seção" : "Pergunta ou nome do campo"
                    }
                    AppTextField {
                        id: helpField
                        Layout.fillWidth: true
                        visible: typeBox.currentValue !== "secao"
                        placeholderText: "Explicação opcional"
                    }
                    AppTextField {
                        id: optionsField
                        Layout.fillWidth: true
                        visible: typeBox.currentValue === "multipla_escolha"
                        placeholderText: "Opções separadas por vírgula"
                    }
                    AppTextField {
                        id: unitField
                        Layout.fillWidth: true
                        visible: typeBox.currentValue === "numero"
                        placeholderText: "Unidade: kg, cm, bpm..."
                    }
                    AppCheckBox {
                        id: requiredCheck
                        visible: typeBox.currentValue !== "secao"
                        text: "Obrigatório ao salvar"
                    }
                    AppCheckBox {
                        id: todayCheck
                        visible: typeBox.currentValue === "data"
                        text: "Preencher com a data de hoje"
                    }
                    Label {
                        Layout.fillWidth: true
                        visible: typeBox.currentValue === "multipla_escolha"
                        text: "Informe pelo menos duas opções."
                        color: "#64748b"
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    AppButton {
                        Layout.fillWidth: true
                        text: dialog.editingIndex >= 0
                              ? "Salvar campo" : "Adicionar campo"
                        highlighted: true
                        onClicked: {
                            let payload = dialog.fieldPayload()
                            if (!payload.label) {
                                editorWarning.text = "Informe o nome do campo."
                                return
                            }
                            if (payload.tipo === "multipla_escolha"
                                    && payload.opcoes.length < 2) {
                                editorWarning.text = "Informe pelo menos duas opções."
                                return
                            }
                            if (dialog.editingIndex >= 0)
                                fichasController.atualizarCampoConstrutor(
                                    dialog.editingIndex, payload
                                )
                            else
                                fichasController.adicionarCampoConstrutor(payload)
                            editorWarning.text = ""
                            dialog.clearEditor()
                        }
                    }
                    Label {
                        id: editorWarning
                        Layout.fillWidth: true
                        color: "#b42318"
                        wrapMode: Text.WordWrap
                        font.pixelSize: 11
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                AppTextField {
                    id: modelName
                    Layout.fillWidth: true
                    placeholderText: "Nome do modelo"
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 10
                    color: "#ffffff"
                    border.color: "#d9e3ef"

                    ListView {
                        id: fieldList
                        anchors.fill: parent
                        anchors.margins: 10
                        clip: true
                        spacing: 7
                        model: fichasController.camposConstrutor
                        ScrollBar.vertical: ScrollBar {}

                        delegate: Rectangle {
                            required property int index
                            required property var modelData
                            width: fieldList.width
                            height: 64
                            radius: 8
                            color: "#f8fafc"
                            border.color: "#d9e3ef"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 6
                                Label {
                                    text: String(index + 1)
                                    color: "#0788c9"
                                    font.weight: Font.Bold
                                }
                                Column {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Label {
                                        width: parent.width
                                        text: modelData.label
                                              + (modelData.obrigatorio ? " *" : "")
                                        color: "#0f172a"
                                        elide: Text.ElideRight
                                        font.weight: Font.DemiBold
                                    }
                                    Label {
                                        text: modelData.tipo.split("_").join(" ")
                                        color: "#64748b"
                                        font.pixelSize: 10
                                    }
                                }
                                AppButton {
                                    text: "↑"
                                    enabled: index > 0
                                    onClicked: fichasController.moverCampoConstrutor(index, -1)
                                }
                                AppButton {
                                    text: "↓"
                                    enabled: index < fieldList.count - 1
                                    onClicked: fichasController.moverCampoConstrutor(index, 1)
                                }
                                AppButton {
                                    text: "Editar"
                                    onClicked: dialog.editField(index, modelData)
                                }
                                AppButton {
                                    text: "Excluir"
                                    variant: "danger"
                                    onClicked: fichasController.removerCampoConstrutor(index)
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: fieldList.count === 0
                            text: "Adicione o primeiro campo usando o painel ao lado."
                            color: "#64748b"
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: fieldList.count + " elemento(s)"
                        color: "#64748b"
                    }
                    AppButton {
                        text: "Concluir e salvar modelo"
                        highlighted: true
                        enabled: fieldList.count > 0 && modelName.text.trim().length > 0
                        onClicked: fichasController.salvarModelo(modelName.text)
                    }
                }
            }
        }
    }

    Connections {
        target: fichasController
        function onEstadoAlterado() {
            if (!fichasController.construindoModelo)
                dialog.close()
        }
        function onModeloImportado(name) {
            dialog.editingExisting = false
            dialog.editingIndex = -1
            modelName.text = name
            dialog.clearEditor()
            dialog.open()
        }
    }
}

