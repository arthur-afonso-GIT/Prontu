import QtQuick
import QtQuick.Controls as Controls

Controls.SpinBox {
    id: control

    implicitHeight: 44
    font.pixelSize: 13
    editable: true

    palette.text: "#0f2747"
    palette.buttonText: "#0f2747"
    palette.highlight: "#dff2fc"
    palette.highlightedText: "#075f92"
    palette.base: "#ffffff"
    palette.button: "#edf7fc"

    background: Rectangle {
        radius: 8
        color: control.enabled ? "#ffffff" : "#f3f6f9"
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? "#0b8fd3" : "#b9cce0"
    }
}
