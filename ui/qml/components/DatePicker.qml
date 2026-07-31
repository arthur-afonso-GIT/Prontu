import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property date selectedDate: new Date()
    property int shownMonth: selectedDate.getMonth()
    property int shownYear: selectedDate.getFullYear()
    readonly property var monthNames: [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    implicitHeight: 314
    implicitWidth: 360

    function sameDay(first, second) {
        return Qt.formatDate(first, "yyyy-MM-dd")
                === Qt.formatDate(second, "yyyy-MM-dd")
    }

    function showDate(value) {
        if (!value || isNaN(value.getTime()))
            return
        selectedDate = new Date(
            value.getFullYear(), value.getMonth(), value.getDate())
        shownMonth = selectedDate.getMonth()
        shownYear = selectedDate.getFullYear()
    }

    function showToday() {
        showDate(new Date())
    }

    function changeMonth(offset) {
        const target = new Date(shownYear, shownMonth + offset, 1)
        shownMonth = target.getMonth()
        shownYear = target.getFullYear()
    }

    Rectangle {
        anchors.fill: parent
        radius: 12
        color: "#ffffff"
        border.width: 1
        border.color: "#b9cce0"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            spacing: 8

            AppButton {
                text: "‹"
                compact: true
                ToolTip.visible: hovered
                ToolTip.text: "Mês anterior"
                onClicked: root.changeMonth(-1)
            }

            Label {
                Layout.fillWidth: true
                text: root.monthNames[root.shownMonth] + " " + root.shownYear
                horizontalAlignment: Text.AlignHCenter
                color: "#0f2747"
                font.pixelSize: 14
                font.weight: Font.DemiBold
            }

            AppButton {
                text: "›"
                compact: true
                ToolTip.visible: hovered
                ToolTip.text: "Próximo mês"
                onClicked: root.changeMonth(1)
            }
        }

        AppButton {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredHeight: 30
            text: "Hoje"
            compact: true
            variant: "secondary"
            visible: !root.sameDay(root.selectedDate, new Date())
            onClicked: root.showToday()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 7
            columnSpacing: 2
            rowSpacing: 0

            Repeater {
                model: ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

                Label {
                    required property string modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 24
                    text: modelData
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    color: "#60738c"
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                }
            }
        }

        MonthGrid {
            id: monthGrid
            Layout.fillWidth: true
            Layout.fillHeight: true
            month: root.shownMonth
            year: root.shownYear
            locale: Qt.locale("pt_BR")
            spacing: 2

            delegate: Rectangle {
                id: dayCell
                required property var model

                readonly property bool sameMonth:
                    model.month === monthGrid.month
                readonly property bool selected:
                    root.sameDay(model.date, root.selectedDate)
                readonly property bool today:
                    root.sameDay(model.date, new Date())

                implicitWidth: 40
                implicitHeight: 34
                radius: 7
                color: selected ? "#0b8fd3"
                     : dayMouse.containsMouse ? "#dff2fc"
                     : "transparent"
                border.width: !selected && today ? 1 : 0
                border.color: "#0b8fd3"

                Behavior on color {
                    ColorAnimation { duration: 100 }
                }

                Label {
                    anchors.centerIn: parent
                    text: dayCell.model.day
                    color: dayCell.selected ? "#ffffff"
                         : dayCell.sameMonth ? "#0f2747" : "#a3afbf"
                    font.pixelSize: 12
                    font.weight: dayCell.selected || dayCell.today
                                 ? Font.Bold : Font.Normal
                }

                MouseArea {
                    id: dayMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.showDate(dayCell.model.date)
                }
            }
        }
    }
}
