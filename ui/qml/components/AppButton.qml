import QtQuick
import QtQuick.Controls

Button {
    id: control

    property string variant: flat ? "ghost"
                                   : highlighted ? "primary" : "secondary"
    property bool compact: false

    readonly property color foreground: {
        if (!enabled)
            return "#94a3b8"
        if (variant === "primary")
            return "#ffffff"
        if (variant === "success")
            return "#ffffff"
        if (variant === "danger")
            return "#be123c"
        if (variant === "ghost")
            return "#475569"
        return "#075985"
    }

    readonly property color backgroundColor: {
        if (!enabled)
            return "#f1f5f9"
        if (variant === "primary")
            return down ? "#0369a1" : hovered ? "#087fba" : "#0b8dca"
        if (variant === "success")
            return down ? "#128c7e" : hovered ? "#169c55" : "#25d366"
        if (variant === "danger")
            return down ? "#ffe4e6" : hovered ? "#fff1f2" : "#fff7f7"
        if (variant === "ghost")
            return hovered ? "#eef4f8" : "transparent"
        return down ? "#d7eefb" : hovered ? "#e4f4fd" : "#eef8fe"
    }

    readonly property color outlineColor: {
        if (!enabled)
            return "#dbe5ef"
        if (variant === "primary")
            return backgroundColor
        if (variant === "success")
            return backgroundColor
        if (variant === "danger")
            return hovered ? "#fda4af" : "#fecdd3"
        if (variant === "ghost")
            return hovered ? "#d8e3ed" : "transparent"
        return hovered ? "#68bde7" : "#a8d8f0"
    }

    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    implicitHeight: compact ? 32 : 40
    implicitWidth: Math.max(compact ? 82 : 106,
                            buttonLabel.implicitWidth + leftPadding + rightPadding)
    leftPadding: compact ? 12 : 16
    rightPadding: compact ? 12 : 16

    contentItem: Label {
        id: buttonLabel
        text: control.text
        color: control.foreground
        font.pixelSize: control.compact ? 11 : 12
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: control.compact ? 7 : 9
        color: control.backgroundColor
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? "#0284c7" : control.outlineColor

        Behavior on color {
            ColorAnimation { duration: 110 }
        }
        Behavior on border.color {
            ColorAnimation { duration: 110 }
        }
    }

    HoverHandler {
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}
