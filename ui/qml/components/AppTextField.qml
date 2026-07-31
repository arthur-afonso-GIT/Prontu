import QtQuick
import QtQuick.Controls as Controls

Controls.TextField {
    id: control

    property bool revealable: false
    property bool passwordVisible: false

    implicitHeight: 44
    leftPadding: 13
    rightPadding: revealable ? 78 : 13
    topPadding: 9
    bottomPadding: 9

    color: enabled ? "#0f2747" : "#7b8ba3"
    placeholderTextColor: "#8091aa"
    selectionColor: "#0788c9"
    selectedTextColor: "#ffffff"
    font.pixelSize: 13
    selectByMouse: true
    echoMode: revealable
              ? (passwordVisible ? TextInput.Normal : TextInput.Password)
              : TextInput.Normal

    background: Rectangle {
        radius: 8
        color: {
            if (!control.enabled)
                return "#f1f5f9"
            if (control.activeFocus)
                return "#ffffff"
            if (control.hovered)
                return "#f8fcff"
            return "#ffffff"
        }
        border.width: control.activeFocus ? 2 : 1
        border.color: {
            if (!control.enabled)
                return "#dbe4ee"
            if (!control.acceptableInput)
                return "#e05265"
            if (control.activeFocus)
                return "#0788c9"
            if (control.hovered)
                return "#7cc4ec"
            return "#c9d8e8"
        }

        Behavior on color {
            ColorAnimation { duration: 120 }
        }
        Behavior on border.color {
            ColorAnimation { duration: 120 }
        }
    }

    Controls.Label {
        visible: control.revealable
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        text: control.passwordVisible ? "Ocultar" : "Mostrar"
        color: revealMouse.containsMouse ? "#0879b8" : "#0b8fd3"
        font.pixelSize: 12
        font.weight: Font.DemiBold

        MouseArea {
            id: revealMouse
            anchors.fill: parent
            anchors.margins: -7
            cursorShape: Qt.PointingHandCursor
            hoverEnabled: true
            onClicked: control.passwordVisible = !control.passwordVisible
        }
    }
}
