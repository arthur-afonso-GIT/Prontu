import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: control

    property string pageKey: ""
    property string iconText: ""
    property bool compact: false
    property bool selected: false

    implicitHeight: 48
    Layout.fillWidth: true
    padding: 0
    hoverEnabled: true

    contentItem: RowLayout {
        anchors.fill: parent
        anchors.leftMargin: control.compact ? 0 : 14
        anchors.rightMargin: control.compact ? 0 : 14
        spacing: 12

        Label {
            Layout.alignment: Qt.AlignVCenter
            Layout.preferredWidth: control.compact ? parent.width : 22
            horizontalAlignment: Text.AlignHCenter
            text: control.iconText
            color: control.selected ? "#ffffff" : "#9fb0ca"
            font.pixelSize: 17
        }

        Label {
            visible: !control.compact
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            text: control.text
            color: control.selected ? "#ffffff" : "#cbd5e1"
            font.pixelSize: 14
            font.weight: control.selected ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
        }
    }

    background: Rectangle {
        radius: 9
        color: control.selected
               ? "#0788c9"
               : control.hovered
                 ? "#1e293b"
                 : "transparent"
        border.width: control.activeFocus ? 1 : 0
        border.color: "#7dd3fc"

        Behavior on color {
            ColorAnimation { duration: 120 }
        }
    }
}
