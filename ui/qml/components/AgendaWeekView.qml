import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property string statusFilter: ""
    signal dayRequested(string dateValue)

    function matchesStatus(value) {
        return statusFilter === ""
            || String(value || "").indexOf(statusFilter) >= 0
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: weekRow.width

        Row {
            id: weekRow
            width: Math.max(root.width, 7 * 164)
            height: Math.max(root.height, 420)
            spacing: 8

            Repeater {
                model: agendaController.diasSemana

                delegate: Rectangle {
                    id: dayCard
                    required property var modelData

                    width: (weekRow.width - weekRow.spacing * 6) / 7
                    height: weekRow.height
                    radius: 9
                    color: "#ffffff"
                    border.width: modelData.hoje ? 2 : 1
                    border.color: modelData.hoje ? "#38a8dc" : "#c9d7e5"

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 52
                            radius: 8
                            color: dayHeaderHover.hovered ? "#dff2fc" : "#edf7fd"

                            Label {
                                anchors.centerIn: parent
                                text: dayCard.modelData.rotulo
                                color: "#164e6f"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                            }

                            HoverHandler {
                                id: dayHeaderHover
                                cursorShape: Qt.PointingHandCursor
                            }
                            TapHandler {
                                onTapped: root.dayRequested(
                                    dayCard.modelData.data
                                )
                            }
                        }

                        ListView {
                            id: dayAppointments
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 5
                            topMargin: 7
                            bottomMargin: 7
                            leftMargin: 6
                            rightMargin: 6
                            model: dayCard.modelData.consultas
                            ScrollBar.vertical: ScrollBar {}

                            delegate: Rectangle {
                                required property var modelData
                                width: dayAppointments.width
                                height: root.matchesStatus(modelData.status)
                                        ? 62 : 0
                                visible: height > 0
                                radius: 7
                                color: appointmentHover.hovered
                                       ? "#eaf6fd" : "#f8fbfe"
                                border.width: 1
                                border.color: modelData.status_color || "#9dcde7"

                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 3
                                    Label {
                                        width: parent.width
                                        text: modelData.horario + " · "
                                              + modelData.paciente
                                        color: "#13213a"
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        width: parent.width
                                        text: modelData.procedimento
                                        color: "#64748b"
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        width: parent.width
                                        text: modelData.status_label
                                        color: modelData.status_color
                                        font.pixelSize: 9
                                        elide: Text.ElideRight
                                    }
                                }

                                HoverHandler {
                                    id: appointmentHover
                                    cursorShape: Qt.PointingHandCursor
                                }
                                TapHandler {
                                    onDoubleTapped: root.dayRequested(
                                        dayCard.modelData.data
                                    )
                                }
                            }

                            Label {
                                anchors.centerIn: parent
                                visible: dayAppointments.count === 0
                                text: "Sem consultas"
                                color: "#94a3b8"
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }
        }
    }
}
