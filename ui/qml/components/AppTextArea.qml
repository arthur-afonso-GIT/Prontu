import QtQuick
import QtQuick.Controls as Controls

Controls.TextArea {
    id: control

    implicitHeight: 88
    leftPadding: 13
    rightPadding: 13
    topPadding: 11
    bottomPadding: 11

    color: enabled ? "#0f2747" : "#7b8ba3"
    placeholderTextColor: "#8091aa"
    selectionColor: "#0788c9"
    selectedTextColor: "#ffffff"
    font.pixelSize: 13
    wrapMode: TextEdit.Wrap

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
}
