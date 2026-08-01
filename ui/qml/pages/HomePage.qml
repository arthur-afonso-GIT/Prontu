import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: page

    property int draggedPatientId: 0
    property string selectedFolder: ""
    property string selectedFolderColor: "#0284c7"

    Component.onCompleted: homeController.carregar()

    Connections {
        target: homeController
        function onFeedback(kind, message) {
            feedbackText.text = message
            feedbackBackground.color = kind === "success" ? "#e8f7ef"
                                     : kind === "warning" ? "#fff7df"
                                     : "#fff0f0"
            feedbackText.color = kind === "success" ? "#137548"
                               : kind === "warning" ? "#8a5b00"
                               : "#b42318"
            feedbackPopup.open()
        }
    }

    function showFolderMenu(name, color) {
        selectedFolder = name
        selectedFolderColor = color
        folderMenuDialog.open()
    }

    function movePatientAtPosition(patientId, dragItem, hotX, hotY) {
        if (patientId <= 0 || !dragItem)
            return false
        for (let index = 0; index < foldersList.count; index++) {
            const card = foldersList.itemAtIndex(index)
            if (!card)
                continue
            const point = card.mapFromItem(dragItem, hotX, hotY)
            if (point.x >= 0 && point.x <= card.width
                    && point.y >= 0 && point.y <= card.height) {
                homeController.moverPaciente(patientId, card.modelData.nome)
                return true
            }
        }
        return false
    }

    SmoothScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: Math.max(page.width, 760)
            spacing: 18

            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                Column {
                    Layout.fillWidth: true
                    spacing: 4
                    Label {
                        text: homeController.saudacao
                        color: "#0f172a"
                        font.pixelSize: 24
                        font.weight: Font.Bold
                    }
                    Label {
                        text: homeController.subtitulo
                        color: "#64748b"
                        font.pixelSize: 13
                    }
                }
                BusyIndicator {
                    running: homeController.ocupado
                    visible: running
                }
                AppButton {
                    text: "Novo paciente"
                    variant: "primary"
                    onClicked: homeController.novoPaciente("Geral")
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: page.width < 850 ? 1 : 3
                columnSpacing: 14
                rowSpacing: 12

                Repeater {
                    model: [
                        {
                            label: "Total de pacientes",
                            value: homeController.totalPacientes,
                            icon: "●",
                            background: "#e0f2fe",
                            color: "#0369a1"
                        },
                        {
                            label: "Consultas hoje",
                            value: homeController.totalConsultas,
                            icon: "▦",
                            background: "#fef3c7",
                            color: "#b45309"
                        },
                        {
                            label: "Retornos pendentes",
                            value: homeController.totalRetornos,
                            icon: "↩",
                            background: "#fce7f3",
                            color: "#be185d"
                        }
                    ]

                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 92
                        radius: 12
                        color: "#ffffff"
                        border.color: "#d9e3ef"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            Column {
                                Layout.fillWidth: true
                                spacing: 5
                                Label {
                                    text: modelData.label
                                    color: "#64748b"
                                    font.pixelSize: 12
                                }
                                Label {
                                    text: modelData.value
                                    color: "#0f172a"
                                    font.pixelSize: 24
                                    font.weight: Font.Bold
                                }
                            }
                            Rectangle {
                                Layout.preferredWidth: 42
                                Layout.preferredHeight: 42
                                radius: 11
                                color: modelData.background
                                Label {
                                    anchors.centerIn: parent
                                    text: modelData.icon
                                    color: modelData.color
                                    font.pixelSize: 20
                                    font.weight: Font.Bold
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Label {
                    Layout.fillWidth: true
                    text: "📁  Pastas clínicas / especialidades"
                    color: "#1e293b"
                    font.pixelSize: 16
                    font.weight: Font.Bold
                }
                Label {
                    visible: page.draggedPatientId > 0
                    text: "Solte o paciente sobre uma pasta"
                    color: "#0369a1"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                }
                AppButton {
                    text: "Nova pasta"
                    variant: "secondary"
                    onClicked: {
                        newFolderName.clear()
                        newFolderDialog.open()
                    }
                }
            }

            ListView {
                id: foldersList
                Layout.fillWidth: true
                Layout.preferredHeight: 132
                orientation: ListView.Horizontal
                spacing: 12
                clip: true
                model: homeController.pastas
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.horizontal: ScrollBar {}

                delegate: Rectangle {
                    id: folderCard
                    required property var modelData
                    width: 174
                    height: 116
                    radius: 10
                    color: dropArea.containsDrag ? "#e0f2fe"
                          : folderHover.hovered ? "#f6fbff" : "#ffffff"
                    border.width: dropArea.containsDrag ? 2 : 1
                    border.color: dropArea.containsDrag
                                  ? "#0284c7" : "#d9e3ef"

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: 4
                        radius: 2
                        color: modelData.cor
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 5

                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                Layout.fillWidth: true
                                text: "📁"
                                font.pixelSize: 16
                            }
                            AppButton {
                                text: "•••"
                                variant: "ghost"
                                compact: true
                                implicitWidth: 34
                                implicitHeight: 28
                                onClicked: page.showFolderMenu(
                                               modelData.nome, modelData.cor)
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: modelData.nome
                            color: "#1e293b"
                            font.pixelSize: 14
                            font.weight: Font.Bold
                            elide: Text.ElideRight
                        }
                        Label {
                            text: modelData.quantidade + " paciente(s)"
                            color: "#64748b"
                            font.pixelSize: 11
                        }
                    }

                    HoverHandler {
                        id: folderHover
                        cursorShape: Qt.PointingHandCursor
                    }
                    TapHandler {
                        onTapped: homeController.abrirPasta(modelData.nome)
                    }
                    DropArea {
                        id: dropArea
                        anchors.fill: parent
                        // Mantém a área receptora acima dos textos, ícones e
                        // botões que compõem visualmente o cartão da pasta.
                        z: 1000
                        keys: ["prontu-patient"]
                        onEntered: function(drag) {
                            if (Number(drag.source
                                       ? drag.source.patientId : 0) > 0
                                    || page.draggedPatientId > 0)
                                drag.acceptProposedAction()
                        }
                        onDropped: function(drop) {
                            const sourceId = Number(drop.source
                                                    ? drop.source.patientId : 0)
                            const patientId = sourceId > 0
                                    ? sourceId : page.draggedPatientId
                            if (patientId > 0) {
                                homeController.moverPaciente(
                                    patientId, modelData.nome)
                                if (drop.source)
                                    drop.source.dropHandled = true
                                drop.acceptProposedAction()
                            }
                            page.draggedPatientId = 0
                        }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: page.width < 1120 ? 1 : 3
                columnSpacing: 14
                rowSpacing: 14

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 292
                    radius: 12
                    color: "#ffffff"
                    border.width: 1
                    border.color: "#c5d4e3"

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 46
                            color: "#ffffff"
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 1
                                color: "#d7e2ed"
                            }
                            Label {
                                anchors.fill: parent
                                leftPadding: 14
                                verticalAlignment: Text.AlignVCenter
                                text: "Próximas consultas (hoje)"
                                color: "#1e293b"
                                font.weight: Font.Bold
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            color: "#f2f6fa"
                            border.width: 1
                            border.color: "#d7e2ed"
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                Label { Layout.preferredWidth: 58; text: "Horário"; color: "#52647c"; font.pixelSize: 11 }
                                Label { Layout.fillWidth: true; text: "Paciente"; color: "#52647c"; font.pixelSize: 11 }
                                Label { Layout.preferredWidth: 100; text: "Status"; color: "#52647c"; font.pixelSize: 11 }
                            }
                        }
                        SmoothListView {
                            id: appointmentsList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: homeController.consultas
                            reuseItems: true
                            cacheBuffer: 160
                            ScrollBar.vertical: ScrollBar {
                                policy: appointmentsList.contentHeight
                                        > appointmentsList.height
                                        ? ScrollBar.AlwaysOn
                                        : ScrollBar.AsNeeded
                            }

                            delegate: Rectangle {
                                required property var modelData
                                width: appointmentsList.width
                                height: 43
                                color: appointmentHover.hovered ? "#edf7ff" : "#ffffff"
                                border.width: 1
                                border.color: "#d4e0eb"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    Label { Layout.preferredWidth: 58; text: modelData.horario; color: "#334155" }
                                    Label { Layout.fillWidth: true; text: modelData.paciente; color: "#0f172a"; elide: Text.ElideRight }
                                    Label { Layout.preferredWidth: 100; text: modelData.status; color: "#137548"; elide: Text.ElideRight }
                                }
                                HoverHandler {
                                    id: appointmentHover
                                    cursorShape: Qt.PointingHandCursor
                                }
                                TapHandler {
                                    acceptedButtons: Qt.LeftButton
                                    gesturePolicy: TapHandler.ReleaseWithinBounds
                                    onDoubleTapped: homeController.abrirConsulta(
                                                         modelData.data,
                                                         modelData.horario)
                                }
                            }
                            Label {
                                anchors.centerIn: parent
                                visible: appointmentsList.count === 0
                                text: "Nenhuma consulta para hoje"
                                color: "#94a3b8"
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 292
                    radius: 12
                    color: "#ffffff"
                    border.width: 1
                    border.color: "#c5d4e3"

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 46
                            color: "#ffffff"
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 1
                                color: "#d7e2ed"
                            }
                            Label {
                                anchors.fill: parent
                                leftPadding: 14
                                verticalAlignment: Text.AlignVCenter
                                text: "Retornos pendentes"
                                color: "#1e293b"
                                font.weight: Font.Bold
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            color: "#f2f6fa"
                            border.width: 1
                            border.color: "#d7e2ed"
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                Label { Layout.fillWidth: true; text: "Paciente"; color: "#52647c"; font.pixelSize: 11 }
                                Label { Layout.preferredWidth: 96; text: "Previsto"; color: "#52647c"; font.pixelSize: 11 }
                                Label { Layout.preferredWidth: 88; text: "Ação"; color: "#52647c"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter }
                            }
                        }
                        SmoothListView {
                            id: returnsList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: homeController.retornos
                            reuseItems: true
                            cacheBuffer: 160
                            ScrollBar.vertical: ScrollBar {
                                policy: returnsList.contentHeight
                                        > returnsList.height
                                        ? ScrollBar.AlwaysOn
                                        : ScrollBar.AsNeeded
                            }

                            delegate: Rectangle {
                                required property var modelData
                                width: returnsList.width
                                height: 48
                                color: "#ffffff"
                                border.width: 1
                                border.color: "#d4e0eb"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 8
                                    spacing: 8
                                    Label { Layout.fillWidth: true; text: modelData.paciente_nome; color: "#0f172a"; elide: Text.ElideRight }
                                    Label {
                                        Layout.preferredWidth: 96
                                        text: modelData.data_texto
                                        color: modelData.atrasado ? "#dc2626" : "#475569"
                                        font.pixelSize: 11
                                    }
                                    AppButton {
                                        Layout.preferredWidth: 88
                                        Layout.preferredHeight: 32
                                        compact: true
                                        variant: "secondary"
                                        text: "Agendar"
                                        onClicked: homeController.agendarRetorno(modelData)
                                    }
                                }
                            }
                            Label {
                                anchors.centerIn: parent
                                visible: returnsList.count === 0
                                text: "Nenhum retorno pendente"
                                color: "#94a3b8"
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 292
                    radius: 12
                    color: "#ffffff"
                    border.width: 1
                    border.color: "#c5d4e3"

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 46
                            color: "#ffffff"
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 1
                                color: "#d7e2ed"
                            }
                            Label {
                                anchors.fill: parent
                                leftPadding: 14
                                verticalAlignment: Text.AlignVCenter
                                text: "Pacientes adicionados recentemente"
                                color: "#1e293b"
                                font.weight: Font.Bold
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            color: "#f2f6fa"
                            border.width: 1
                            border.color: "#d7e2ed"
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                Label { Layout.fillWidth: true; text: "Paciente"; color: "#52647c"; font.pixelSize: 11 }
                                Label { Layout.preferredWidth: 108; text: "Pasta"; color: "#52647c"; font.pixelSize: 11 }
                            }
                        }
                        SmoothListView {
                            id: recentList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: page.draggedPatientId === 0
                            model: homeController.pacientesRecentes
                            reuseItems: true
                            cacheBuffer: 160
                            ScrollBar.vertical: ScrollBar {
                                policy: recentList.contentHeight
                                        > recentList.height
                                        ? ScrollBar.AlwaysOn
                                        : ScrollBar.AsNeeded
                            }

                            delegate: Rectangle {
                                id: recentRow
                                required property var modelData
                                property int patientId: Number(modelData.id || 0)
                                width: recentList.width
                                height: 43
                                color: recentHover.hovered ? "#edf7ff" : "#ffffff"
                                border.width: 1
                                border.color: "#d4e0eb"
                                opacity: dragHandler.active ? 0.88 : 1
                                scale: dragHandler.active ? 1.02 : 1
                                z: dragHandler.active ? 100 : 0

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    Label {
                                        Layout.fillWidth: true
                                        text: modelData.nome
                                        color: "#0f172a"
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        Layout.preferredWidth: 108
                                        text: modelData.pasta
                                        color: "#0369a1"
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                    }
                                }
                                Rectangle {
                                    id: dragProxy
                                    property int patientId: recentRow.patientId
                                    property bool dropHandled: false
                                    width: recentRow.width
                                    height: recentRow.height
                                    radius: 6
                                    color: "#dff2ff"
                                    border.width: 1
                                    border.color: "#38a7e0"
                                    opacity: dragHandler.active ? 0.72 : 0
                                    visible: dragHandler.active
                                    z: 200

                                    Drag.active: dragHandler.active
                                    // A fonte do evento precisa ser o mesmo item que
                                    // efetivamente se move. Assim a pasta sempre recebe
                                    // o ID do paciente, inclusive após rolagem da lista.
                                    Drag.source: dragProxy
                                    Drag.keys: ["prontu-patient"]
                                    Drag.supportedActions: Qt.MoveAction
                                    // O ponto de soltura acompanha exatamente o lugar
                                    // onde o usuário segurou a linha. Antes ele ficava
                                    // no centro do cartão largo e atingia a pasta apenas
                                    // quando o mouse era deslocado para o lado.
                                    Drag.hotSpot.x: Math.max(
                                                        0, Math.min(
                                                            width,
                                                            dragHandler.centroid
                                                            .pressPosition.x))
                                    Drag.hotSpot.y: Math.max(
                                                        0, Math.min(
                                                            height,
                                                            dragHandler.centroid
                                                            .pressPosition.y))

                                    Label {
                                        anchors.centerIn: parent
                                        width: parent.width - 24
                                        text: recentRow.modelData.nome
                                        color: "#075985"
                                        font.weight: Font.DemiBold
                                        horizontalAlignment: Text.AlignHCenter
                                        elide: Text.ElideRight
                                    }
                                }
                                HoverHandler {
                                    id: recentHover
                                    cursorShape: dragHandler.active
                                                 ? Qt.ClosedHandCursor
                                                 : Qt.OpenHandCursor
                                }
                                TapHandler {
                                    onDoubleTapped: homeController.abrirPaciente(
                                                         modelData.id)
                                }
                                DragHandler {
                                    id: dragHandler
                                    // Apenas a cópia visual se move. A linha permanece na
                                    // tabela até o banco confirmar a mudança.
                                    target: dragProxy
                                    onActiveChanged: {
                                        if (active) {
                                            dragProxy.x = 0
                                            dragProxy.y = 0
                                            dragProxy.dropHandled = false
                                            page.draggedPatientId =
                                                    recentRow.patientId
                                        } else {
                                            const patientId = recentRow.patientId
                                            const hotX = dragHandler.centroid
                                                         .pressPosition.x
                                            const hotY = dragHandler.centroid
                                                         .pressPosition.y
                                            Qt.callLater(function() {
                                                // Caminho de confirmação independente
                                                // de onDropped. Isso evita perder o gesto
                                                // dentro de listas roláveis ou com escala.
                                                if (!dragProxy.dropHandled)
                                                    page.movePatientAtPosition(
                                                        patientId, dragProxy,
                                                        hotX, hotY)
                                                dragProxy.x = 0
                                                dragProxy.y = 0
                                                if (page.draggedPatientId
                                                        === recentRow.patientId)
                                                    page.draggedPatientId = 0
                                            })
                                        }
                                    }
                                }
                            }
                            Label {
                                anchors.centerIn: parent
                                visible: recentList.count === 0
                                text: "Nenhum paciente cadastrado"
                                color: "#94a3b8"
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: newFolderDialog
        anchors.centerIn: parent
        width: Math.min(440, page.width - 40)
        modal: true
        title: "Nova pasta"
        standardButtons: Dialog.NoButton

        contentItem: ColumnLayout {
            spacing: 12
            Label { text: "Nome da especialidade ou grupo" }
            AppTextField {
                id: newFolderName
                Layout.fillWidth: true
                placeholderText: "Ex.: Ortopedia"
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: newFolderDialog.close()
                }
                AppButton {
                    text: "Criar pasta"
                    variant: "primary"
                    onClicked: {
                        homeController.criarPasta(
                            newFolderName.text, "#0284c7")
                        newFolderDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: folderMenuDialog
        anchors.centerIn: parent
        width: Math.min(460, page.width - 40)
        modal: true
        title: page.selectedFolder
        standardButtons: Dialog.NoButton

        contentItem: ColumnLayout {
            spacing: 12
            AppButton {
                Layout.fillWidth: true
                text: "Abrir pacientes desta pasta"
                variant: "secondary"
                onClicked: {
                    folderMenuDialog.close()
                    homeController.abrirPasta(page.selectedFolder)
                }
            }
            AppButton {
                Layout.fillWidth: true
                text: "Cadastrar paciente nesta pasta"
                variant: "secondary"
                onClicked: {
                    folderMenuDialog.close()
                    homeController.novoPaciente(page.selectedFolder)
                }
            }
            AppButton {
                Layout.fillWidth: true
                visible: page.selectedFolder.toLowerCase() !== "geral"
                text: "Renomear pasta"
                variant: "secondary"
                onClicked: {
                    renameFolderName.text = page.selectedFolder
                    folderMenuDialog.close()
                    renameDialog.open()
                }
            }
            Label {
                text: "Cor da pasta"
                color: "#334155"
                font.weight: Font.DemiBold
            }
            RowLayout {
                Repeater {
                    model: ["#0284c7", "#7c3aed", "#db2777", "#ea580c", "#16a34a", "#475569"]
                    delegate: Rectangle {
                        required property string modelData
                        width: 38
                        height: 38
                        radius: 19
                        color: modelData
                        border.width: page.selectedFolderColor === modelData ? 3 : 1
                        border.color: page.selectedFolderColor === modelData
                                      ? "#0f172a" : "#ffffff"
                        TapHandler {
                            onTapped: {
                                folderMenuDialog.close()
                                homeController.mudarCorPasta(
                                    page.selectedFolder, modelData)
                            }
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                }
            }
            AppButton {
                Layout.fillWidth: true
                visible: page.selectedFolder.toLowerCase() !== "geral"
                text: "Excluir “" + page.selectedFolder
                      + "”? Os pacientes dessa pasta voltarão para Geral."
                onClicked: {
                    folderMenuDialog.close()
                    deleteDialog.open()
                }
            }
            AppButton {
                Layout.alignment: Qt.AlignRight
                text: "Fechar"
                variant: "ghost"
                onClicked: folderMenuDialog.close()
            }
        }
    }

    Dialog {
        id: renameDialog
        anchors.centerIn: parent
        width: Math.min(440, page.width - 40)
        modal: true
        title: "Renomear pasta"
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 12
            AppTextField { id: renameFolderName; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: renameDialog.close()
                }
                AppButton {
                    text: "Salvar"
                    variant: "primary"
                    onClicked: {
                        homeController.renomearPasta(
                            page.selectedFolder, renameFolderName.text)
                        renameDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteDialog
        anchors.centerIn: parent
        width: Math.min(480, page.width - 40)
        modal: true
        title: "Excluir pasta"
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 14
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Excluir “" + page.selectedFolder
                      + "”? Os pacientes dessa pasta voltarão para Geral."
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    text: "Cancelar"
                    variant: "ghost"
                    onClicked: deleteDialog.close()
                }
                AppButton {
                    text: "Excluir pasta"
                    variant: "danger"
                    onClicked: {
                        homeController.excluirPasta(page.selectedFolder)
                        deleteDialog.close()
                    }
                }
            }
        }
    }

    Popup {
        id: feedbackPopup
        x: Math.max(16, page.width - width - 16)
        y: 16
        width: Math.min(450, page.width - 32)
        height: 62
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
