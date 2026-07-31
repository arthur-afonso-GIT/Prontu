import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: window

    width: 980
    height: 650
    minimumWidth: 760
    minimumHeight: 560
    visible: true
    title: "Acessar o Prontu"
    color: "#eef4fa"

    palette.window: "#eef4fa"
    palette.windowText: "#0f172a"
    palette.base: "#ffffff"
    palette.text: "#0f172a"
    palette.button: "#eef8fe"
    palette.buttonText: "#075985"
    palette.highlight: "#d9effb"
    palette.highlightedText: "#075985"
    palette.mid: "#a8d8f0"
    palette.light: "#f8fbfe"
    palette.dark: "#68bde7"

    property int currentTab: 0
    property string feedbackKind: ""
    property string feedbackMessage: ""
    readonly property bool compact: width < 860
    readonly property color primary: "#0788c9"
    readonly property color navy: "#0f1f38"
    readonly property color borderColor: "#d6e1ed"
    readonly property color muted: "#64748b"

    onClosing: function(close) {
        if (!loginController.estaAutenticado)
            loginController.cancelar()
    }

    Connections {
        target: loginController

        function onFeedback(kind, message) {
            window.feedbackKind = kind
            window.feedbackMessage = message
        }

        function onAutenticado() {
            window.close()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#eef4fa"

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                visible: !window.compact
                Layout.fillHeight: true
                Layout.preferredWidth: 360
                color: window.navy

                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#102442" }
                        GradientStop { position: 1; color: "#0b172a" }
                    }
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 42
                    spacing: 18

                    Item { Layout.preferredHeight: 18 }

                    RowLayout {
                        spacing: 14

                        Rectangle {
                            width: 58
                            height: 58
                            radius: 15
                            color: "#18345d"

                            Image {
                                anchors.fill: parent
                                anchors.margins: 7
                                source: appLogoUrl
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                mipmap: true
                            }
                        }

                        Label {
                            text: "Prontu"
                            color: "#ffffff"
                            font.pixelSize: 30
                            font.weight: Font.Bold
                        }
                    }

                    Item { Layout.preferredHeight: 14 }

                    Label {
                        Layout.fillWidth: true
                        text: "Sua clínica organizada em um só lugar."
                        color: "#ffffff"
                        wrapMode: Text.WordWrap
                        font.pixelSize: 28
                        font.weight: Font.Bold
                        lineHeight: 1.12
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "Agenda, pacientes, prontuários e financeiro com acesso seguro para toda a equipe."
                        color: "#b8c8dc"
                        wrapMode: Text.WordWrap
                        font.pixelSize: 15
                        lineHeight: 1.35
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        spacing: 9
                        Rectangle {
                            width: 9
                            height: 9
                            radius: 5
                            color: "#34d399"
                        }
                        Label {
                            text: "Conexão protegida"
                            color: "#d7e2ef"
                            font.pixelSize: 13
                        }
                    }
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ScrollView {
                    anchors.fill: parent
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        height: Math.max(implicitHeight, window.height)
                        spacing: 0

                        Item { Layout.fillHeight: true }

                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: Math.min(
                                520, Math.max(440, window.width - 80))
                            Layout.preferredHeight: accessContent.implicitHeight + 54
                            radius: 18
                            color: "#ffffff"
                            border.width: 1
                            border.color: window.borderColor

                            ColumnLayout {
                                id: accessContent
                                anchors.fill: parent
                                anchors.margins: 27
                                spacing: 15

                                RowLayout {
                                    visible: window.compact
                                    spacing: 10

                                    Image {
                                        width: 38
                                        height: 38
                                        source: appLogoUrl
                                        fillMode: Image.PreserveAspectFit
                                    }
                                    Label {
                                        text: "Prontu"
                                        color: window.navy
                                        font.pixelSize: 24
                                        font.weight: Font.Bold
                                    }
                                }

                                Label {
                                    text: loginController.ativacaoPronta
                                          ? "Crie seu login"
                                          : "Acesse sua clínica"
                                    color: "#0f172a"
                                    font.pixelSize: 25
                                    font.weight: Font.Bold
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: loginController.ativacaoPronta
                                          ? "A chave foi validada. Defina o e-mail e a senha do proprietário."
                                          : "Entre com seu e-mail, use um convite ou ative a clínica neste dispositivo."
                                    color: window.muted
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: 13
                                    lineHeight: 1.25
                                }

                                Rectangle {
                                    visible: window.feedbackMessage.length > 0
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: feedbackText.implicitHeight + 22
                                    radius: 9
                                    color: window.feedbackKind === "success" ? "#e8f7ef"
                                         : window.feedbackKind === "warning" ? "#fff7df"
                                         : "#fff0f0"
                                    border.width: 1
                                    border.color: window.feedbackKind === "success" ? "#b7e5ca"
                                                : window.feedbackKind === "warning" ? "#f2d58b"
                                                : "#f4b8b5"

                                    Label {
                                        id: feedbackText
                                        anchors.fill: parent
                                        anchors.margins: 11
                                        text: window.feedbackMessage
                                        color: window.feedbackKind === "success" ? "#137548"
                                             : window.feedbackKind === "warning" ? "#8a5b00"
                                             : "#b42318"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 12
                                    }
                                }

                                RowLayout {
                                    visible: !loginController.ativacaoPronta
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Repeater {
                                        model: ["Entrar", "Usar convite", "Ativar clínica"]

                                        AppButton {
                                            required property string modelData
                                            required property int index
                                            Layout.fillWidth: true
                                            text: modelData
                                            flat: true
                                            onClicked: {
                                                window.currentTab = index
                                                window.feedbackMessage = ""
                                            }
                                            contentItem: Label {
                                                text: parent.text
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                                color: window.currentTab === index
                                                       ? window.primary : "#52647c"
                                                font.pixelSize: 12
                                                font.weight: window.currentTab === index
                                                             ? Font.DemiBold : Font.Normal
                                            }
                                            background: Rectangle {
                                                radius: 8
                                                color: window.currentTab === index
                                                       ? "#e7f5fc"
                                                       : parent.hovered ? "#f3f7fb" : "transparent"
                                                border.width: window.currentTab === index ? 1 : 0
                                                border.color: "#addcf4"
                                            }
                                        }
                                    }
                                }

                                StackLayout {
                                    visible: !loginController.ativacaoPronta
                                    Layout.fillWidth: true
                                    currentIndex: window.currentTab

                                    ColumnLayout {
                                        spacing: 11

                                        Label { text: "E-mail"; color: "#243650"; font.pixelSize: 12 }
                                        AppTextField {
                                            id: loginEmail
                                            Layout.fillWidth: true
                                            placeholderText: "seuemail@clinica.com"
                                            inputMethodHints: Qt.ImhEmailCharactersOnly
                                        }

                                        Label { text: "Senha"; color: "#243650"; font.pixelSize: 12 }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 8
                                            AppTextField {
                                                id: loginPassword
                                                Layout.fillWidth: true
                                                revealable: true
                                                placeholderText: "Sua senha"
                                                onAccepted: loginController.entrar(
                                                    loginEmail.text,
                                                    text,
                                                    rememberMe.checked)
                                            }
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            AppCheckBox {
                                                id: rememberMe
                                                text: "Lembrar de mim"
                                                checked: true
                                            }
                                            Item { Layout.fillWidth: true }
                                            AppButton {
                                                text: "Esqueci minha senha"
                                                flat: true
                                                onClicked: {
                                                    recoveryEmail.text = loginEmail.text
                                                    recoveryDialog.open()
                                                }
                                            }
                                        }

                                        AppButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 44
                                            text: "Entrar"
                                            enabled: !loginController.ocupado
                                            onClicked: loginController.entrar(
                                                loginEmail.text,
                                                loginPassword.text,
                                                rememberMe.checked)
                                            highlighted: true
                                        }
                                    }

                                    ColumnLayout {
                                        spacing: 10

                                        Label {
                                            Layout.fillWidth: true
                                            text: "Use o código enviado pelo proprietário para criar sua própria senha."
                                            color: window.muted
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 12
                                        }
                                        Label { text: "Código"; color: "#243650"; font.pixelSize: 12 }
                                        AppTextField {
                                            id: inviteCode
                                            Layout.fillWidth: true
                                            placeholderText: "PRONTU-XXXXXXXX"
                                        }
                                        Label { text: "E-mail"; color: "#243650"; font.pixelSize: 12 }
                                        AppTextField {
                                            id: inviteEmail
                                            Layout.fillWidth: true
                                            placeholderText: "O mesmo e-mail do convite"
                                            inputMethodHints: Qt.ImhEmailCharactersOnly
                                        }
                                        Label { text: "Senha"; color: "#243650"; font.pixelSize: 12 }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            AppTextField {
                                                id: invitePassword
                                                Layout.fillWidth: true
                                                revealable: true
                                                placeholderText: "Pelo menos 8 caracteres"
                                            }
                                        }
                                        Label { text: "Confirmar senha"; color: "#243650"; font.pixelSize: 12 }
                                        AppTextField {
                                            id: inviteConfirmation
                                            Layout.fillWidth: true
                                            revealable: true
                                            placeholderText: "Repita a senha"
                                        }
                                        AppButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 44
                                            text: "Criar meu acesso"
                                            enabled: !loginController.ocupado
                                            highlighted: true
                                            onClicked: loginController.aceitarConvite(
                                                inviteCode.text,
                                                inviteEmail.text,
                                                invitePassword.text,
                                                inviteConfirmation.text)
                                        }
                                    }

                                    ColumnLayout {
                                        spacing: 11

                                        Label {
                                            Layout.fillWidth: true
                                            text: "Use esta opção somente no primeiro dispositivo do proprietário."
                                            color: window.muted
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 12
                                        }
                                        Label {
                                            text: "Chave de ativação"
                                            color: "#243650"
                                            font.pixelSize: 12
                                        }
                                        AppTextField {
                                            id: activationKey
                                            Layout.fillWidth: true
                                            placeholderText: "PRONTU-..."
                                            onAccepted: loginController.ativarChave(text)
                                        }
                                        AppButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 44
                                            text: "Validar chave"
                                            enabled: !loginController.ocupado
                                            highlighted: true
                                            onClicked: loginController.ativarChave(
                                                activationKey.text)
                                        }
                                    }
                                }

                                ColumnLayout {
                                    visible: loginController.ativacaoPronta
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Label { text: "E-mail do proprietário"; color: "#243650"; font.pixelSize: 12 }
                                    AppTextField {
                                        id: ownerEmail
                                        Layout.fillWidth: true
                                        placeholderText: "seuemail@clinica.com"
                                        inputMethodHints: Qt.ImhEmailCharactersOnly
                                    }
                                    Label { text: "Senha"; color: "#243650"; font.pixelSize: 12 }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        AppTextField {
                                            id: ownerPassword
                                            Layout.fillWidth: true
                                            revealable: true
                                            placeholderText: "Pelo menos 8 caracteres"
                                        }
                                    }
                                    Label { text: "Confirmar senha"; color: "#243650"; font.pixelSize: 12 }
                                    AppTextField {
                                        id: ownerConfirmation
                                        Layout.fillWidth: true
                                        revealable: true
                                        placeholderText: "Repita a senha"
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        AppButton {
                                            Layout.fillWidth: true
                                            text: "Cancelar ativação"
                                            variant: "ghost"
                                            enabled: !loginController.ocupado
                                            onClicked: {
                                                loginController.cancelarCriacaoProprietario()
                                                window.currentTab = 2
                                                window.feedbackMessage = ""
                                            }
                                        }
                                        AppButton {
                                            Layout.fillWidth: true
                                            text: "Criar meu login"
                                            enabled: !loginController.ocupado
                                            highlighted: true
                                            onClicked: loginController.criarProprietario(
                                                ownerEmail.text,
                                                ownerPassword.text,
                                                ownerConfirmation.text)
                                        }
                                    }
                                }

                                RowLayout {
                                    visible: loginController.ocupado
                                    Layout.alignment: Qt.AlignHCenter
                                    spacing: 9
                                    BusyIndicator {
                                        running: true
                                        implicitWidth: 26
                                        implicitHeight: 26
                                    }
                                    Label {
                                        text: "Conectando com segurança..."
                                        color: window.muted
                                        font.pixelSize: 12
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }
    }

    Dialog {
        id: recoveryDialog
        anchors.centerIn: parent
        width: Math.min(420, window.width - 48)
        modal: true
        title: "Recuperar acesso"
        standardButtons: Dialog.NoButton

        ColumnLayout {
            width: parent.width
            spacing: 12

            Label {
                Layout.fillWidth: true
                text: "Informe seu e-mail. Se houver uma conta vinculada, enviaremos um link seguro para criar uma nova senha."
                color: window.muted
                wrapMode: Text.WordWrap
            }
            AppTextField {
                id: recoveryEmail
                Layout.fillWidth: true
                placeholderText: "seuemail@clinica.com"
                inputMethodHints: Qt.ImhEmailCharactersOnly
            }
            RowLayout {
                Layout.fillWidth: true
                AppButton {
                    Layout.fillWidth: true
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: recoveryDialog.close()
                }
                AppButton {
                    Layout.fillWidth: true
                    text: "Enviar link"
                    enabled: !loginController.ocupado
                    highlighted: true
                    onClicked: {
                        loginController.solicitarRedefinicao(
                            recoveryEmail.text)
                        recoveryDialog.close()
                    }
                }
            }
        }
    }
}

