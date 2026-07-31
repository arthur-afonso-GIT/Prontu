import QtQuick
import QtQuick.Controls as Controls

Controls.ComboBox {
    id: control

    implicitHeight: 44
    leftPadding: 12
    rightPadding: 34
    font.pixelSize: 13

    palette.text: "#0f2747"
    palette.buttonText: "#0f2747"
    palette.windowText: "#0f2747"
    palette.highlight: "#dff2fc"
    palette.highlightedText: "#075f92"
    palette.base: "#ffffff"
    palette.button: "#ffffff"
    palette.window: "#ffffff"

    background: Rectangle {
        radius: 8
        color: control.enabled
               ? (control.hovered ? "#f7fbfe" : "#ffffff")
               : "#f3f6f9"
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus
                      ? "#0b8fd3"
                      : (control.hovered ? "#74bce5" : "#b9cce0")

        Behavior on border.color {
            ColorAnimation { duration: 100 }
        }
    }
}
