import QtQuick
import QtQuick.Controls as Controls

Controls.CheckBox {
    id: control

    implicitHeight: 36
    spacing: 9
    font.pixelSize: 13

    indicator: Rectangle {
        implicitWidth: 20
        implicitHeight: 20
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: 5
        color: control.checked ? "#0b8fd3" : "#ffffff"
        border.width: control.activeFocus ? 2 : 1
        border.color: control.checked
                      ? "#0b8fd3"
                      : (control.hovered ? "#74bce5" : "#aebfd1")

        Text {
            anchors.centerIn: parent
            text: "✓"
            visible: control.checked
            color: "#ffffff"
            font.pixelSize: 14
            font.bold: true
        }
    }

    contentItem: Text {
        text: control.text
        color: control.enabled ? "#18324f" : "#8b99aa"
        font: control.font
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing
        elide: Text.ElideRight
    }
}
