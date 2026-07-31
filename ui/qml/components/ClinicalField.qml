import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property var fieldData: ({})
    property var fieldValue
    signal edited(var value)

    implicitHeight: content.implicitHeight

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 6

        Label {
            Layout.fillWidth: true
            visible: root.fieldData.tipo === "secao"
            text: root.fieldData.label || "Seção"
            color: "#0788c9"
            font.pixelSize: 15
            font.weight: Font.Bold
            topPadding: 12
            bottomPadding: 4
        }

        Label {
            Layout.fillWidth: true
            visible: root.fieldData.tipo !== "secao"
            text: (root.fieldData.label || "Campo")
                  + (root.fieldData.obrigatorio ? " *" : "")
            color: "#0f172a"
            font.pixelSize: 13
            font.weight: Font.DemiBold
            wrapMode: Text.WordWrap
        }

        Loader {
            id: editor
            Layout.fillWidth: true
            active: root.fieldData.tipo !== "secao"
            sourceComponent: {
                switch (root.fieldData.tipo) {
                case "texto_longo": return longText
                case "checkbox": return checkValue
                case "multipla_escolha": return choiceValue
                default: return shortText
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: root.fieldData.tipo !== "secao"
                     && String(root.fieldData.ajuda || "").length > 0
            text: root.fieldData.ajuda || ""
            color: "#64748b"
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
    }

    Component {
        id: shortText
        AppTextField {
            id: input
            placeholderText: root.fieldData.placeholder
                             || (root.fieldData.tipo === "data"
                                 ? "DD/MM/AAAA" : "")
            inputMethodHints: root.fieldData.tipo === "numero"
                              ? Qt.ImhFormattedNumbersOnly
                              : Qt.ImhNone
            Component.onCompleted: text = String(root.fieldValue ?? "")
            Connections {
                target: root
                function onFieldValueChanged() {
                    if (!input.activeFocus)
                        input.text = String(root.fieldValue ?? "")
                }
            }
            onTextEdited: root.edited(text)
        }
    }

    Component {
        id: longText
        ScrollView {
            implicitHeight: 100
            AppTextArea {
                id: input
                wrapMode: TextEdit.Wrap
                placeholderText: root.fieldData.placeholder || ""
                Component.onCompleted: text = String(root.fieldValue ?? "")
                Connections {
                    target: root
                    function onFieldValueChanged() {
                        if (!input.activeFocus)
                            input.text = String(root.fieldValue ?? "")
                    }
                }
                onTextChanged: {
                    if (activeFocus)
                        root.edited(text)
                }
            }
        }
    }

    Component {
        id: checkValue
        AppCheckBox {
            id: input
            text: root.fieldData.texto_checkbox
                  || root.fieldData.texto_opcao || "Sim"
            Component.onCompleted: checked = Boolean(root.fieldValue)
            Connections {
                target: root
                function onFieldValueChanged() {
                    input.checked = Boolean(root.fieldValue)
                }
            }
            onToggled: root.edited(checked)
        }
    }

    Component {
        id: choiceValue
        AppComboBox {
            id: input
            model: root.fieldData.opcoes || []
            Component.onCompleted: {
                let index = find(String(root.fieldValue ?? ""))
                currentIndex = index >= 0 ? index : -1
            }
            Connections {
                target: root
                function onFieldValueChanged() {
                    let index = input.find(String(root.fieldValue ?? ""))
                    input.currentIndex = index >= 0 ? index : -1
                }
            }
            onActivated: root.edited(currentText)
        }
    }
}

