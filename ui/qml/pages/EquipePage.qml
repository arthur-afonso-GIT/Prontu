import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page

    property string pendingAction: ""
    property string pendingId: ""
    property string pendingName: ""
    property string roleMemberId: ""
    property string inviteCode: ""
    property string inviteEmail: ""

    Component.onCompleted: equipeController.carregar()

    Connections {
        target: equipeController

        function onFeedback(kind, message) {
            feedbackText.text = message
            feedbackBox.color = kind === "success" ? "#e8f7ef"
                              : kind === "warning" ? "#fff7df" : "#fff0f0"
            feedbackText.color = kind === "success" ? "#137548"
                               : kind === "warning" ? "#8a5b00" : "#b42318"
            feedbackPopup.open()
        }

        function onConviteCriado(code, email) {
            page.inviteCode = code
            page.inviteEmail = email || inviteEmailField.text
            inviteNameField.clear()
            inviteEmailField.clear()
            inviteDialog.open()
        }
    }

    function requestConfirmation(action, identifier, name) {
        pendingAction = action
        pendingId = identifier
        pendingName = name
        confirmationDialog.title = action === "cancelInvite"
                                 ? "Cancelar convite"
                                 : "Revogar acesso"
        confirmationText.text = action === "cancelInvite"
                              ? "Cancelar o convite de " + name + "?"
                              : "Revogar o acesso de " + name + "?"
        confirmationDialog.open()
    }

    ScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: Math.max(page.width, 760)
            spacing: 16

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 78
                radius: 12
                color: "#f0f9ff"
                border.color: "#bae6fd"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 14

                    Rectangle {
                        Layout.preferredWidth: 44
                        Layout.preferredHeight: 44
                        radius: 12
                        color: "#dbeafe"
                        Label {
                            anchors.centerIn: parent
                            text: "👥"
                            font.pixelSize: 22
                        }
                    }
                    Column {
                        Layout.fillWidth: true
                        spacing: 4
                        Label {
                            text: equipeController.resumoVagas
                            color: "#0f172a"
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                        }
                        Label {
                            text: "Cada pessoa usa seu próprio e-mail e senha."
                            color: "#64748b"
                            font.pixelSize: 12
                        }
                    }
                    BusyIndicator {
                        running: equipeController.ocupado
                        visible: running
                    }
                    AppButton {
                        text: "Atualizar"
                        enabled: !equipeController.ocupado
                        onClicked: equipeController.carregar()
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: page.width < 1040 ? 1 : 2
                columnSpacing: 16
                rowSpacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.width < 1040 ? 430 : 510
                    radius: 12
                    color: "#ffffff"
                    border.color: "#d9e3ef"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 10

                        Label {
                            text: "Integrantes com acesso"
                            color: "#0f172a"
                            font.pixelSize: 17
                            font.weight: Font.Bold
                        }
                        Label {
                            text: equipeController.totalMembros
                                  + " pessoa(s) com acesso ativo"
                            color: "#64748b"
                            font.pixelSize: 12
                        }

                        ListView {
                            id: membersList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 8
                            model: equipeController.membrosModel
                            ScrollBar.vertical: ScrollBar {}

                            delegate: Rectangle {
                                required property string memberId
                                required property string memberName
                                required property string memberEmail
                                required property string memberRole
                                required property string memberRoleLabel
                                required property bool isOwner

                                width: membersList.width
                                height: 78
                                radius: 9
                                color: memberMouse.hovered ? "#f6fbff" : "#ffffff"
                                border.color: "#dce6f1"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 10

                                    Rectangle {
                                        Layout.preferredWidth: 38
                                        Layout.preferredHeight: 38
                                        radius: 19
                                        color: isOwner ? "#e0f2fe" : "#eef2ff"
                                        Label {
                                            anchors.centerIn: parent
                                            text: (memberName || memberEmail || "?")
                                                  .charAt(0).toUpperCase()
                                            color: "#075985"
                                            font.weight: Font.Bold
                                        }
                                    }
                                    Column {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Label {
                                            width: parent.width
                                            text: memberName || "Nome não informado"
                                            color: "#0f172a"
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }
                                        Label {
                                            width: parent.width
                                            text: memberEmail
                                            color: "#64748b"
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                    }
                                    Rectangle {
                                        Layout.preferredWidth: 96
                                        Layout.preferredHeight: 28
                                        radius: 14
                                        color: isOwner ? "#e0f2fe" : "#f1f5f9"
                                        Label {
                                            anchors.centerIn: parent
                                            text: memberRoleLabel
                                            color: isOwner ? "#0369a1" : "#475569"
                                            font.pixelSize: 11
                                            font.weight: Font.DemiBold
                                        }
                                    }
                                    AppButton {
                                        visible: !isOwner
                                        text: "Alterar papel"
                                        onClicked: {
                                            page.roleMemberId = memberId
                                            roleBox.currentIndex =
                                                memberRole === "secretaria" ? 1 : 0
                                            roleDialog.open()
                                        }
                                    }
                                    AppButton {
                                        visible: !isOwner
                                        text: "Revogar"
                                        variant: "danger"
                                        onClicked: page.requestConfirmation(
                                            "revokeMember", memberId,
                                            memberName || memberEmail
                                        )
                                    }
                                }

                                HoverHandler { id: memberMouse }
                            }

                            Label {
                                anchors.centerIn: parent
                                visible: equipeController.totalMembros === 0
                                         && !equipeController.ocupado
                                text: "Nenhum integrante encontrado."
                                color: "#64748b"
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.width < 1040 ? 360 : 510
                    radius: 12
                    color: "#ffffff"
                    border.color: "#d9e3ef"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 8

                        Label {
                            text: "Convidar integrante"
                            color: "#0f172a"
                            font.pixelSize: 17
                            font.weight: Font.Bold
                        }
                        Label {
                            Layout.fillWidth: true
                            text: "A pessoa receberá um código único para criar a própria senha."
                            color: "#64748b"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                        }
                        Label { text: "Nome" }
                        AppTextField {
                            id: inviteNameField
                            Layout.fillWidth: true
                            placeholderText: "Ex.: Maria Silva"
                        }
                        Label { text: "E-mail" }
                        AppTextField {
                            id: inviteEmailField
                            Layout.fillWidth: true
                            placeholderText: "nome@clinica.com"
                            inputMethodHints: Qt.ImhEmailCharactersOnly
                        }
                        Label { text: "Papel" }
                        AppComboBox {
                            id: inviteRoleBox
                            Layout.fillWidth: true
                            textRole: "label"
                            valueRole: "value"
                            model: [
                                { label: "Profissional", value: "profissional" },
                                { label: "Secretária", value: "secretaria" }
                            ]
                        }
                        Label {
                            Layout.fillWidth: true
                            text: equipeController.disponiveis > 0
                                  ? equipeController.disponiveis + " vaga(s) disponível(is)"
                                  : "Não há vagas disponíveis"
                            color: equipeController.disponiveis > 0
                                   ? "#137548" : "#b42318"
                            font.pixelSize: 12
                        }
                        Item { Layout.fillHeight: true }
                        AppButton {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 42
                            text: "Gerar convite"
                            highlighted: true
                            enabled: !equipeController.ocupado
                                     && equipeController.disponiveis > 0
                            onClicked: equipeController.criarConvite(
                                inviteNameField.text,
                                inviteEmailField.text,
                                inviteRoleBox.currentValue
                            )
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 300
                radius: 12
                color: "#ffffff"
                border.color: "#d9e3ef"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            Layout.fillWidth: true
                            text: "Convites pendentes"
                            color: "#0f172a"
                            font.pixelSize: 17
                            font.weight: Font.Bold
                        }
                        Label {
                            text: equipeController.totalConvites + " pendente(s)"
                            color: "#64748b"
                        }
                    }

                    ListView {
                        id: invitesList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 7
                        model: equipeController.convitesModel
                        ScrollBar.vertical: ScrollBar {}

                        delegate: Rectangle {
                            required property string inviteId
                            required property string inviteName
                            required property string inviteEmail
                            required property string inviteRole
                            required property string inviteRoleLabel
                            required property string inviteExpires

                            width: invitesList.width
                            height: 66
                            radius: 8
                            color: inviteMouse.hovered ? "#f6fbff" : "#ffffff"
                            border.color: "#dce6f1"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 11
                                spacing: 12
                                Column {
                                    Layout.fillWidth: true
                                    Label {
                                        width: parent.width
                                        text: inviteName || inviteEmail
                                        color: "#0f172a"
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        width: parent.width
                                        text: inviteEmail
                                        color: "#64748b"
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                    }
                                }
                                Label {
                                    Layout.preferredWidth: 90
                                    text: inviteRoleLabel
                                    color: "#475569"
                                }
                                Label {
                                    Layout.preferredWidth: 115
                                    text: "Expira: " + inviteExpires
                                    color: "#64748b"
                                    font.pixelSize: 11
                                }
                                AppButton {
                                    text: "Novo código"
                                    onClicked: equipeController.renovarConvite(
                                        inviteId, inviteEmail
                                    )
                                }
                                AppButton {
                                    text: "Cancelar"
                                    variant: "danger"
                                    onClicked: page.requestConfirmation(
                                        "cancelInvite", inviteId,
                                        inviteName || inviteEmail
                                    )
                                }
                            }
                            HoverHandler { id: inviteMouse }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: equipeController.totalConvites === 0
                                     && !equipeController.ocupado
                            text: "Nenhum convite pendente."
                            color: "#64748b"
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: inviteDialog
        anchors.centerIn: parent
        width: Math.min(500, page.width - 40)
        modal: true
        title: "Convite criado"
        standardButtons: Dialog.Close

        ColumnLayout {
            width: parent.width
            spacing: 10
            Label {
                Layout.fillWidth: true
                text: "Envie estes dados para a pessoa. O código expira em 7 dias e é exibido somente agora."
                wrapMode: Text.WordWrap
                color: "#64748b"
            }
            Label { text: "Código de convite"; font.weight: Font.DemiBold }
            RowLayout {
                Layout.fillWidth: true
                AppTextField {
                    Layout.fillWidth: true
                    text: page.inviteCode
                    readOnly: true
                    selectByMouse: true
                }
                AppButton {
                    text: "Copiar código"
                    highlighted: true
                    onClicked: equipeController.copiarCodigo(page.inviteCode)
                }
            }
            Label { text: "E-mail"; font.weight: Font.DemiBold }
            AppTextField {
                Layout.fillWidth: true
                text: page.inviteEmail
                readOnly: true
                selectByMouse: true
            }
        }
    }

    Dialog {
        id: roleDialog
        anchors.centerIn: parent
        modal: true
        title: "Alterar papel"
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: equipeController.alterarPapel(
            page.roleMemberId, roleBox.currentValue
        )
        ColumnLayout {
            Label { text: "Escolha o novo nível de acesso:" }
            AppComboBox {
                id: roleBox
                Layout.preferredWidth: 280
                textRole: "label"
                valueRole: "value"
                model: [
                    { label: "Profissional", value: "profissional" },
                    { label: "Secretária", value: "secretaria" }
                ]
            }
        }
    }

    Dialog {
        id: confirmationDialog
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: {
            if (page.pendingAction === "cancelInvite")
                equipeController.cancelarConvite(page.pendingId)
            else
                equipeController.revogarMembro(page.pendingId)
        }
        Label {
            id: confirmationText
            width: 330
            wrapMode: Text.WordWrap
        }
    }

    Popup {
        id: feedbackPopup
        anchors.centerIn: parent
        width: Math.min(440, page.width - 40)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            id: feedbackBox
            radius: 10
            border.color: "#d9e3ef"
        }
        contentItem: Label {
            id: feedbackText
            padding: 16
            wrapMode: Text.WordWrap
        }
    }
}

