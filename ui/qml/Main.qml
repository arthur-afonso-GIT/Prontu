import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: window

    QtObject {
        id: fallbackAppController

        readonly property string logoUrl: ""
        readonly property bool podeVerFichas: false
        readonly property bool podeGerenciarEquipe: false
        readonly property string paginaAtual: ""
        readonly property string nomeClinica: ""
        readonly property string papelAtual: ""
        readonly property string planoAtual: ""
        readonly property string tituloPagina: ""
        readonly property string subtituloPagina: ""

        function navegar(_pagina) {}
    }

    QtObject {
        id: fallbackHomeController

        signal abrirPacienteSolicitado(int patientId)
        signal novaPessoaSolicitada(string folderName)
        signal abrirPastaSolicitada(string folderName)
        signal abrirConsultaSolicitada(string dateValue, string timeValue)
        signal agendarRetornoSolicitado(var returnData)
    }

    QtObject {
        id: fallbackFinancialController

        readonly property string alertaPagamentos: ""

        function carregar() {}
    }

    readonly property var controller:
        (typeof appController !== "undefined" && appController)
        ? appController : fallbackAppController
    readonly property var homeEvents:
        (typeof homeController !== "undefined" && homeController)
        ? homeController : fallbackHomeController
    readonly property var financialEvents:
        (typeof financeiroController !== "undefined" && financeiroController)
        ? financeiroController : fallbackFinancialController

    Component.onCompleted: window.financialEvents.carregar()

    Connections {
        target: window.homeEvents

        function onAbrirPacienteSolicitado(patientId) {
            window.controller.navegar("pacientes")
            Qt.callLater(function() {
                if (patientsLoader.item)
                    patientsLoader.item.openEditor(patientId)
            })
        }

        function onNovaPessoaSolicitada(folderName) {
            window.controller.navegar("pacientes")
            Qt.callLater(function() {
                if (patientsLoader.item)
                    patientsLoader.item.newPatientInFolder(folderName)
            })
        }

        function onAbrirPastaSolicitada(folderName) {
            window.controller.navegar("pacientes")
            Qt.callLater(function() {
                if (patientsLoader.item)
                    patientsLoader.item.openFolder(folderName)
            })
        }

        function onAbrirConsultaSolicitada(dateValue, timeValue) {
            window.controller.navegar("agenda")
            agendaController.definirData(dateValue)
        }

        function onAgendarRetornoSolicitado(returnData) {
            window.controller.navegar("agenda")
            Qt.callLater(function() {
                if (agendaLoader.item)
                    agendaLoader.item.openReturn(returnData)
            })
        }
    }

    Connections {
        target: (typeof agendaController !== "undefined")
                ? agendaController : null

        function onFeedback(kind, _message) {
            if (kind === "success")
                window.financialEvents.carregar()
        }
    }

    width: 1280
    height: 800
    minimumWidth: 900
    minimumHeight: 620
    visible: true
    title: "Prontu — Gerenciamento Inteligente"
    color: "#f5f8fc"

    palette.window: "#f5f8fc"
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

    readonly property bool compactNavigation: width < 1080
    readonly property color primary: "#0788c9"
    readonly property color navy: "#0f172a"
    readonly property color textPrimary: "#0f172a"
    readonly property color textMuted: "#64748b"
    readonly property color borderColor: "#d9e3ef"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: window.compactNavigation ? 76 : 238
            color: window.navy

            Behavior on Layout.preferredWidth {
                NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 7

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 68

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 12

                        Rectangle {
                            width: 44
                            height: 44
                            radius: 11
                            color: "#172a4a"

                            Image {
                                anchors.fill: parent
                                anchors.margins: 5
                                source: window.controller.logoUrl
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                mipmap: true
                            }
                        }

                        Label {
                            visible: !window.compactNavigation
                            text: "Prontu"
                            color: "#ffffff"
                            font.pixelSize: 22
                            font.weight: Font.Bold
                        }
                    }
                }

                Repeater {
                    model: [
                        { key: "home", label: "Painel Principal", icon: "⌂", visible: true },
                        { key: "pacientes", label: "Pacientes", icon: "●", visible: true },
                        { key: "agenda", label: "Agenda de Consultas", icon: "▦", visible: true },
                        { key: "fichas", label: "Fichas Clínicas", icon: "▤", visible: window.controller.podeVerFichas },
                        { key: "financeiro", label: "Financeiro", icon: "$", visible: true },
                        { key: "equipe", label: "Equipe", icon: "◆", visible: window.controller.podeGerenciarEquipe },
                        { key: "configuracoes", label: "Configurações", icon: "⚙", visible: true }
                    ]

                    delegate: NavButton {
                        required property var modelData
                        visible: modelData.visible
                        pageKey: modelData.key
                        text: modelData.label
                        iconText: modelData.icon
                        compact: window.compactNavigation
                        selected: window.controller.paginaAtual === pageKey
                        indicatorVisible: modelData.key === "financeiro"
                                          && window.financialEvents.alertaPagamentos !== ""
                        indicatorColor:
                            window.financialEvents.alertaPagamentos === "atrasado"
                            ? "#ef4444" : "#f59e0b"
                        onClicked: window.controller.navegar(pageKey)

                        ToolTip.visible: compact && hovered
                        ToolTip.text: {
                            if (modelData.key !== "financeiro"
                                    || !indicatorVisible)
                                return text
                            return text + (
                                window.financialEvents.alertaPagamentos === "atrasado"
                                ? " — há pagamento atrasado"
                                : " — há pagamento pendente"
                            )
                        }
                        ToolTip.delay: 450
                    }
                }

                Item { Layout.fillHeight: true }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: window.compactNavigation ? 52 : 74
                    radius: 10
                    color: "#172033"

                    Column {
                        visible: !window.compactNavigation
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 3

                        Label {
                            width: parent.width
                            text: window.controller.nomeClinica
                            color: "#e2e8f0"
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }
                        Label {
                            text: window.controller.papelAtual + " · " + window.controller.planoAtual
                            color: "#8494ad"
                            font.pixelSize: 11
                        }
                    }

                    Label {
                        visible: window.compactNavigation
                        anchors.centerIn: parent
                        text: "●"
                        color: "#34d399"
                        font.pixelSize: 15
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#f5f8fc"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: window.width < 1100 ? 22 : 32
                spacing: 22

                RowLayout {
                    Layout.fillWidth: true

                    Column {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: window.controller.tituloPagina
                            color: window.textPrimary
                            font.pixelSize: 27
                            font.weight: Font.Bold
                        }
                        Label {
                            text: window.controller.subtituloPagina
                            color: window.textMuted
                            font.pixelSize: 13
                        }
                    }

                    Rectangle {
                        implicitWidth: statusContent.implicitWidth + 28
                        implicitHeight: 36
                        radius: 18
                        color: "#e8f7ef"
                        border.color: "#b7e5ca"

                        Row {
                            id: statusContent
                            anchors.centerIn: parent
                            spacing: 7
                            Label { text: "●"; color: "#15935c"; font.pixelSize: 11 }
                            Label {
                                text: "Sessão segura ativa"
                                color: "#137548"
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 16
                    color: "#ffffff"
                    border.width: 1
                    border.color: window.borderColor
                    visible: window.controller.paginaAtual !== "pacientes"
                             && window.controller.paginaAtual !== "home"
                             && window.controller.paginaAtual !== "agenda"
                             && window.controller.paginaAtual !== "fichas"
                             && window.controller.paginaAtual !== "financeiro"
                             && window.controller.paginaAtual !== "equipe"
                             && window.controller.paginaAtual !== "configuracoes"

                    ColumnLayout {
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 48, 560)
                        spacing: 14

                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter
                            width: 58
                            height: 58
                            radius: 16
                            color: "#e7f5fc"

                            Label {
                                anchors.centerIn: parent
                                text: "✓"
                                color: window.primary
                                font.pixelSize: 28
                                font.weight: Font.Bold
                            }
                        }

                        Label {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: window.controller.tituloPagina
                            color: window.textPrimary
                            font.pixelSize: 20
                            font.weight: Font.DemiBold
                        }

                        Label {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            text: "A estrutura visual QML está pronta para receber esta tela sem alterar a versão estável do aplicativo."
                            color: window.textMuted
                            font.pixelSize: 14
                            lineHeight: 1.25
                        }
                    }
                }

                Loader {
                    id: homeLoader
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    active: window.controller.paginaAtual === "home"
                    visible: active
                    source: "pages/HomePage.qml"
                }

                Loader {
                    id: patientsLoader
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    active: window.controller.paginaAtual === "pacientes"
                    visible: active
                    source: "pages/PatientsPage.qml"
                }

                Loader {
                    id: agendaLoader
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    active: window.controller.paginaAtual === "agenda"
                    visible: active
                    source: "pages/AgendaPage.qml"
                }

                Loader {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    active: window.controller.paginaAtual === "fichas"
                    visible: active
                    source: "pages/FichasPage.qml"
                }

                Loader {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    active: window.controller.paginaAtual === "financeiro"
                    visible: active
                    source: "pages/FinanceiroPage.qml"
                }

                Loader {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    active: window.controller.paginaAtual === "equipe"
                    visible: active
                    source: "pages/EquipePage.qml"
                }

                Loader {
                    id: configuracoesLoader
                    objectName: "configuracoesLoader"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    active: window.controller.paginaAtual === "configuracoes"
                    visible: active
                    source: "pages/ConfiguracoesPage.qml"
                }
            }
        }
    }
}
