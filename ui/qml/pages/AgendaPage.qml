import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page

    property string statusFilter: ""
    property bool hideAvailable: false
    property int pendingReturnId: 0
    property int returnDecisionId: 0
    property string returnDecisionPatient: ""

    function matchesFilter(statusValue) {
        return statusFilter === "" || statusValue.indexOf(statusFilter) >= 0
    }

    function openNewAppointment(timeValue) {
        pendingReturnId = 0
        appointmentTime.currentIndex = Math.max(
            0, agendaController.horarios.indexOf(timeValue || "08:00")
        )
        patientInput.currentIndex = -1
        patientInput.editText = ""
        procedureInput.currentIndex = 0
        durationInput.currentIndex = 1
        statusInput.currentIndex = 0
        notesInput.text = ""
        appointmentDialog.open()
    }

    function openReturn(returnData) {
        pendingReturnId = Number(returnData.id || 0)
        if (returnData.data_prevista)
            agendaController.definirData(returnData.data_texto)
        patientInput.currentIndex = -1
        patientInput.editText = returnData.paciente_nome || ""
        procedureInput.currentIndex = Math.max(
            0, agendaController.procedimentos.indexOf("Retorno"))
        durationInput.currentIndex = 1
        statusInput.currentIndex = 0
        notesInput.text = returnData.motivo || ""
        appointmentDialog.open()
    }

    function requestReturn(returnId, patientName) {
        returnDecisionId = Number(returnId || 0)
        returnDecisionPatient = patientName || ""
        var suggested = new Date()
        suggested.setDate(suggested.getDate() + 30)
        returnCalendar.showDate(suggested)
        returnDateInput.text = Qt.formatDate(suggested, "dd/MM/yyyy")
        returnDateDialog.open()
    }

    function dateFromText(value) {
        const parts = String(value || "").split("/")
        if (parts.length !== 3)
            return null
        const day = Number(parts[0])
        const month = Number(parts[1])
        const year = Number(parts[2])
        const parsed = new Date(year, month - 1, day)
        if (parsed.getFullYear() !== year
                || parsed.getMonth() !== month - 1
                || parsed.getDate() !== day)
            return null
        return parsed
    }

    Component.onCompleted: agendaController.carregar()

    Connections {
        target: agendaController
        function onRetornoProntoParaAgendar(returnData) {
            returnDateDialog.close()
            page.openReturn(returnData)
        }
        function onConfirmacaoHorarioPassado(dataConsulta, horario) {
            pastAppointmentText.text =
                "O horário de " + horario + " do dia " + dataConsulta
                + " já passou.\n\nDeseja agendar mesmo assim?"
            pastAppointmentDialog.open()
        }
        function onConflitoHorario(dataConsulta, horarios) {
            conflictAppointmentText.text =
                "Já existe uma consulta no dia " + dataConsulta
                + " ocupando " + (horarios || "o horário escolhido") + ".\n\n"
                + "Escolha outro horário para continuar."
            conflictAppointmentDialog.open()
        }
        function onFeedback(kind, message) {
            feedbackText.text = message
            feedbackBackground.color = kind === "success" ? "#e8f7ef"
                                     : kind === "warning" ? "#fff7df"
                                     : "#fff0f0"
            feedbackText.color = kind === "success" ? "#137548"
                               : kind === "warning" ? "#8a5b00"
                               : "#b42318"
            feedbackPopup.open()
            if (kind === "success")
                appointmentDialog.close()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            radius: 12
            color: "#ffffff"
            border.width: 1
            border.color: "#d9e3ef"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                AppButton {
                    text: "‹"
                    variant: "secondary"
                    compact: true
                    implicitWidth: 38
                    onClicked: agendaController.navegarDias(-1)
                }
                AppButton {
                    text: "Hoje"
                    variant: "secondary"
                    compact: true
                    onClicked: agendaController.irParaHoje()
                }

                Item { Layout.fillWidth: true }

                Label {
                    text: agendaController.tituloPeriodo
                    color: "#13213a"
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                }

                Item { Layout.fillWidth: true }

                AppButton {
                    text: "›"
                    variant: "secondary"
                    compact: true
                    implicitWidth: 38
                    onClicked: agendaController.navegarDias(1)
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: summaryLayout.implicitHeight + 20
            radius: 12
            color: "#ffffff"
            border.width: 1
            border.color: "#d9e3ef"

            ColumnLayout {
                id: summaryLayout
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Column {
                    Layout.fillWidth: true
                    spacing: 3

                    Label {
                        text: agendaController.tituloResumo
                        color: "#17223b"
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                    }
                    Label {
                        text: agendaController.totalConsultas + " consulta(s) · "
                              + agendaController.totalConfirmadas + " confirmada(s) · "
                              + agendaController.totalPendentes + " pendente(s) · "
                              + agendaController.totalRealizadas + " realizada(s)"
                        color: "#64748b"
                        font.pixelSize: 11
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Item {
                        Layout.fillWidth: true
                    }

                    AppComboBox {
                        Layout.preferredWidth: 150
                        model: [
                            "Visão diária",
                            "Visão semanal",
                            "Visão mensal"
                        ]
                        currentIndex: agendaController.modo === "semana" ? 1
                                      : agendaController.modo === "mes" ? 2 : 0
                        onActivated: {
                            const modes = ["dia", "semana", "mes"]
                            agendaController.definirModo(modes[currentIndex])
                        }
                    }

                    AppComboBox {
                        Layout.preferredWidth: 165
                        model: [
                            "Todos os status",
                            "Agendadas",
                            "Confirmadas",
                            "Em atendimento",
                            "Realizadas",
                            "Canceladas",
                            "Faltas"
                        ]
                        onActivated: {
                            const values = [
                                "", "Agendado", "Confirmado", "Atendimento",
                                "Realizada", "Cancelada", "Faltou"
                            ]
                            page.statusFilter = values[currentIndex]
                        }
                    }

                    AppCheckBox {
                        visible: agendaController.modo === "dia"
                        text: "Ocultar horários livres"
                        onToggled: page.hideAvailable = checked
                    }

                    AppButton {
                        text: "Nova consulta"
                        variant: "primary"
                        onClicked: page.openNewAppointment("08:00")
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: agendaController.modo === "semana" ? 1
                          : agendaController.modo === "mes" ? 2 : 0

            Rectangle {
                radius: 12
                color: "#ffffff"
                border.width: 1
                border.color: "#c5d4e3"

                ListView {
                    id: scheduleList
                    anchors.fill: parent
                    anchors.margins: 1
                    clip: true
                    model: agendaController.model
                    spacing: 0
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {}

                    delegate: Rectangle {
                    id: scheduleRow

                    required property string time
                    required property bool available
                    required property bool continuation
                    required property string patient
                    required property string procedure
                    required property string duration
                    required property string statusValue
                    required property string statusLabel
                    required property string statusColor
                    required property string notes
                    required property int pendingReturnDecisionId

                    readonly property bool rowVisible:
                        !continuation
                        && (!available || !page.hideAvailable)
                        && (available || page.matchesFilter(statusValue))

                    width: scheduleList.width
                    height: rowVisible ? (available ? 43 : 74) : 0
                    visible: height > 0
                    color: rowHover.hovered ? "#f3f9fe" : "#ffffff"
                    border.width: rowVisible ? 1 : 0
                    border.color: "#dbe5f0"

                    Behavior on color { ColorAnimation { duration: 100 } }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        spacing: 12

                        Label {
                            Layout.preferredWidth: 58
                            text: scheduleRow.time
                            color: "#253650"
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            visible: !scheduleRow.available
                            Layout.preferredWidth: 4
                            Layout.fillHeight: true
                            Layout.topMargin: 7
                            Layout.bottomMargin: 7
                            radius: 2
                            color: scheduleRow.statusColor
                        }

                        Column {
                            Layout.fillWidth: true
                            spacing: 4

                            Label {
                                text: scheduleRow.available
                                      ? "Horário disponível"
                                      : scheduleRow.patient
                                color: scheduleRow.available ? "#8aa0ba" : "#13213a"
                                font.pixelSize: scheduleRow.available ? 12 : 14
                                font.weight: scheduleRow.available
                                             ? Font.Normal : Font.DemiBold
                                font.italic: scheduleRow.available
                            }
                            Label {
                                visible: !scheduleRow.available
                                text: scheduleRow.procedure + " (" + scheduleRow.duration + ")"
                                color: "#64748b"
                                font.pixelSize: 11
                            }
                        }

                        Rectangle {
                            visible: !scheduleRow.available
                            implicitWidth: statusText.implicitWidth + 20
                            implicitHeight: 28
                            radius: 14
                            color: Qt.alpha(scheduleRow.statusColor, 0.10)
                            border.width: 1
                            border.color: Qt.alpha(scheduleRow.statusColor, 0.28)

                            Label {
                                id: statusText
                                anchors.centerIn: parent
                                text: scheduleRow.statusLabel
                                color: scheduleRow.statusColor
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                            }
                        }

                        RowLayout {
                            visible: scheduleRow.pendingReturnDecisionId > 0
                            spacing: 7

                            AppButton {
                                text: "Agendar retorno"
                                variant: "secondary"
                                compact: true
                                implicitWidth: 126
                                onClicked: page.requestReturn(
                                    scheduleRow.pendingReturnDecisionId,
                                    scheduleRow.patient
                                )
                            }
                            AppButton {
                                text: "Não retornará"
                                variant: "danger"
                                compact: true
                                implicitWidth: 118
                                onClicked: {
                                    page.returnDecisionId =
                                        scheduleRow.pendingReturnDecisionId
                                    page.returnDecisionPatient =
                                        scheduleRow.patient
                                    noReturnDialog.open()
                                }
                            }
                        }

                        AppComboBox {
                            visible: !scheduleRow.available
                            Layout.preferredWidth: 170
                            model: agendaController.statusDisponiveis
                            currentIndex: Math.max(
                                0,
                                agendaController.statusDisponiveis.indexOf(
                                    scheduleRow.statusValue
                                )
                            )
                            onActivated: agendaController.atualizarStatus(
                                scheduleRow.time, currentText
                            )
                        }
                    }

                    HoverHandler {
                        id: rowHover
                        cursorShape: scheduleRow.available
                                     ? Qt.PointingHandCursor : Qt.ArrowCursor
                    }
                    TapHandler {
                        enabled: scheduleRow.available
                        onTapped: page.openNewAppointment(scheduleRow.time)
                    }
                }

                    BusyIndicator {
                        anchors.centerIn: parent
                        visible: agendaController.ocupado
                        running: visible
                    }
                }
            }

            AgendaWeekView {
                statusFilter: page.statusFilter
                onDayRequested: function(dateValue) {
                    agendaController.abrirDia(dateValue)
                }
            }

            AgendaMonthView {
                statusFilter: page.statusFilter
                onDayRequested: function(dateValue) {
                    agendaController.abrirDia(dateValue)
                }
            }
        }
    }

    Dialog {
        id: appointmentDialog
        anchors.centerIn: parent
        width: Math.min(540, page.width - 32)
        modal: true
        title: "Nova consulta · " + agendaController.dataSelecionada
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            width: parent.width
            spacing: 10

            Label { text: "Paciente cadastrado" }
            AppComboBox {
                id: patientInput
                Layout.fillWidth: true
                editable: true
                model: agendaController.pacientes
                selectTextByMouse: true
                inputMethodHints: Qt.ImhNoPredictiveText
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Horário" }
                    AppComboBox {
                        id: appointmentTime
                        Layout.fillWidth: true
                        model: agendaController.horarios
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Duração estimada" }
                    AppComboBox {
                        id: durationInput
                        Layout.fillWidth: true
                        model: agendaController.duracoes
                    }
                }
            }

            Label { text: "Procedimento / tipo de consulta" }
            AppComboBox {
                id: procedureInput
                Layout.fillWidth: true
                model: agendaController.procedimentos
            }

            Label { text: "Status inicial" }
            AppComboBox {
                id: statusInput
                Layout.fillWidth: true
                model: agendaController.statusDisponiveis
            }

            Label { text: "Observações (opcional)" }
            AppTextField {
                id: notesInput
                Layout.fillWidth: true
                placeholderText: "Ex.: paciente solicitou preferência em encaixes"
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 8
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: appointmentDialog.close()
                }
                AppButton {
                    text: "Confirmar agendamento"
                    variant: "primary"
                    enabled: !agendaController.ocupado
                    onClicked: agendaController.criarConsulta({
                        paciente: patientInput.editText,
                        horario: appointmentTime.currentText,
                        duracao: durationInput.currentText,
                        procedimento: procedureInput.currentText,
                        status: statusInput.currentText,
                        observacao: notesInput.text,
                        retorno_id: page.pendingReturnId || null
                    })
                }
            }
        }
    }

    Dialog {
        id: pastAppointmentDialog
        anchors.centerIn: parent
        width: Math.min(430, page.width - 32)
        modal: true
        title: "Horário já passou"
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        property bool confirmed: false

        onOpened: confirmed = false
        onClosed: {
            if (!confirmed)
                agendaController.cancelarConsultaNoPassado()
        }

        ColumnLayout {
            width: parent.width
            spacing: 16

            Label {
                id: pastAppointmentText
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#334155"
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Voltar e corrigir"
                    variant: "secondary"
                    onClicked: pastAppointmentDialog.close()
                }
                AppButton {
                    text: "Agendar mesmo assim"
                    variant: "primary"
                    onClicked: {
                        pastAppointmentDialog.confirmed = true
                        pastAppointmentDialog.close()
                        agendaController.confirmarConsultaNoPassado()
                    }
                }
            }
        }
    }

    Dialog {
        id: conflictAppointmentDialog
        anchors.centerIn: parent
        width: Math.min(430, page.width - 32)
        modal: true
        title: "Horário indisponível"
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            width: parent.width
            spacing: 16

            Label {
                id: conflictAppointmentText
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#334155"
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Escolher outro horário"
                    variant: "primary"
                    onClicked: conflictAppointmentDialog.close()
                }
            }
        }
    }

    Dialog {
        id: returnDateDialog
        anchors.centerIn: parent
        width: Math.min(480, page.width - 32)
        modal: true
        title: "Agendar retorno"
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            width: parent.width
            spacing: 12

            Label {
                Layout.fillWidth: true
                text: "Escolha a data prevista para o retorno de "
                      + page.returnDecisionPatient + ":"
                wrapMode: Text.WordWrap
            }

            DatePicker {
                id: returnCalendar
                Layout.fillWidth: true
                Layout.preferredHeight: 292
                onSelectedDateChanged: {
                    if (returnDateDialog.visible)
                        returnDateInput.text =
                            Qt.formatDate(selectedDate, "dd/MM/yyyy")
                }
            }

            Label {
                Layout.fillWidth: true
                text: "Data escolhida"
                color: "#334155"
                font.pixelSize: 11
                font.weight: Font.DemiBold
            }

            AppTextField {
                id: returnDateInput
                Layout.fillWidth: true
                placeholderText: "dia/mês/ano"
                selectByMouse: true
                inputMethodHints: Qt.ImhDate
                validator: RegularExpressionValidator {
                    regularExpression: /\d{2}\/\d{2}\/\d{4}/
                }
                onEditingFinished: {
                    const parsed = page.dateFromText(text)
                    if (parsed)
                        returnCalendar.showDate(parsed)
                }
            }
            Label {
                Layout.fillWidth: true
                text: "A sugestão inicial é 30 dias após hoje. "
                      + "Você pode escolher no calendário ou digitar outra data."
                color: "#64748b"
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Cancelar"
                    variant: "secondary"
                    onClicked: returnDateDialog.close()
                }
                AppButton {
                    text: "Continuar para a Agenda"
                    variant: "primary"
                    enabled: !agendaController.ocupado
                    onClicked: agendaController.prepararAgendamentoRetorno(
                        page.returnDecisionId,
                        returnDateInput.text,
                        page.returnDecisionPatient
                    )
                }
            }
        }
    }

    Dialog {
        id: noReturnDialog
        anchors.centerIn: parent
        width: Math.min(430, page.width - 32)
        modal: true
        title: "Confirmar que não haverá retorno"
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape

        ColumnLayout {
            width: parent.width
            spacing: 16

            Label {
                Layout.fillWidth: true
                text: "Deseja registrar que " + page.returnDecisionPatient
                      + " não retornará após esta consulta?"
                wrapMode: Text.WordWrap
                color: "#334155"
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Cancelar"
                    variant: "secondary"
                    onClicked: noReturnDialog.close()
                }
                AppButton {
                    text: "Confirmar decisão"
                    variant: "danger"
                    enabled: !agendaController.ocupado
                    onClicked: {
                        noReturnDialog.close()
                        agendaController.marcarSemRetorno(
                            page.returnDecisionId
                        )
                    }
                }
            }
        }
    }

    Popup {
        id: feedbackPopup
        x: Math.max(16, page.width - width - 16)
        y: 16
        width: Math.min(440, page.width - 32)
        height: 58
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        Timer {
            interval: 3400
            running: feedbackPopup.opened
            onTriggered: feedbackPopup.close()
        }

        background: Rectangle {
            id: feedbackBackground
            radius: 9
            border.width: 1
            border.color: Qt.darker(color, 1.08)
        }

        Label {
            id: feedbackText
            anchors.fill: parent
            anchors.margins: 14
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
            font.pixelSize: 12
            font.weight: Font.DemiBold
        }
    }
}

