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

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            spacing: 2

            Repeater {
                model: ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
                Rectangle {
                    required property string modelData
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#edf4fa"
                    border.width: 1
                    border.color: "#c9d7e5"
                    Label {
                        anchors.centerIn: parent
                        text: modelData
                        color: "#52657f"
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 7
            columnSpacing: 2
            rowSpacing: 2

            Repeater {
                model: agendaController.diasMes

                delegate: Rectangle {
                    id: monthCell
                    required property var modelData

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 72
                    color: !modelData.mes_atual ? "#f8fafc"
                         : monthHover.hovered ? "#eef8fe" : "#ffffff"
                    border.width: modelData.hoje ? 2 : 1
                    border.color: modelData.hoje ? "#38a8dc" : "#d3deea"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 7
                        spacing: 3

                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                text: monthCell.modelData.dia
                                color: monthCell.modelData.mes_atual
                                       ? "#17233a" : "#a3afbf"
                                font.pixelSize: 12
                                font.weight: monthCell.modelData.hoje
                                             ? Font.Bold : Font.DemiBold
                            }
                            Item { Layout.fillWidth: true }
                            Rectangle {
                                visible: monthCell.modelData.total > 0
                                width: 24
                                height: 20
                                radius: 10
                                color: "#dff2fc"
                                Label {
                                    anchors.centerIn: parent
                                    text: monthCell.modelData.total
                                    color: "#0369a1"
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                }
                            }
                        }

                        Repeater {
                            model: monthCell.modelData.consultas.slice(0, 2)
                            Label {
                                required property var modelData
                                Layout.fillWidth: true
                                visible: root.matchesStatus(modelData.status)
                                text: modelData.horario + " " + modelData.paciente
                                color: modelData.status_color
                                font.pixelSize: 9
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: monthCell.modelData.total > 2
                            text: "+" + (monthCell.modelData.total - 2)
                                  + " consulta(s)"
                            color: "#64748b"
                            font.pixelSize: 9
                        }
                        Item { Layout.fillHeight: true }
                    }

                    HoverHandler {
                        id: monthHover
                        cursorShape: Qt.PointingHandCursor
                    }
                    TapHandler {
                        onTapped: root.dayRequested(monthCell.modelData.data)
                    }
                }
            }
        }
    }
}
