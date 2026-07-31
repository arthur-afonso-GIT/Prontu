import QtQuick
import QtQuick.Controls as Controls

Controls.RadioButton {
    id: control

    implicitHeight: 36
    spacing: 9
    font.pixelSize: 13

    indicator: Rectangle {
        implicitWidth: 20
        implicitHeight: 20
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: width / 2
        color: "#ffffff"
        border.width: control.activeFocus ? 2 : 1
        border.color: control.checked
                      ? "#0b8fd3"
                      : (control.hovered ? "#74bce5" : "#aebfd1")

        Rectangle {
            anchors.centerIn: parent
            width: 10
            height: 10
            radius: width / 2
            visible: control.checked
            color: "#0b8fd3"
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
