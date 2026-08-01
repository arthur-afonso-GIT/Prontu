import QtQuick
import QtQuick.Controls

Item {
    id: root

    property var model: []
    property string textRole: ""
    property string valueRole: ""
    property int currentIndex: -1
    property var currentValue: undefined
    property alias editText: searchField.text
    property alias placeholderText: searchField.placeholderText
    property int maximumVisibleItems: 6
    property var filteredItems: []

    signal activated(int index, var value)

    implicitHeight: 44

    function normalized(value) {
        var text = String(value || "").trim().toLocaleLowerCase()
        try {
            return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        } catch (error) {
            return text
        }
    }

    function itemLabel(item) {
        if (root.textRole && item && typeof item === "object")
            return String(item[root.textRole] || "")
        return String(item || "")
    }

    function itemValue(item) {
        if (root.valueRole && item && typeof item === "object")
            return item[root.valueRole]
        return itemLabel(item)
    }

    function findSourceIndex(value) {
        var expected = normalized(value)
        if (!expected)
            return -1

        var source = root.model || []
        for (var index = 0; index < source.length; index++) {
            if (normalized(itemValue(source[index])) === expected
                    || normalized(itemLabel(source[index])) === expected)
                return index
        }
        return -1
    }

    function rebuildFilter(openPopup) {
        var source = root.model || []
        var query = normalized(searchField.text)
        var matches = []

        for (var index = 0; index < source.length; index++) {
            var patientName = itemLabel(source[index])
            if (!query || normalized(patientName).indexOf(query) === 0) {
                matches.push({
                    "sourceIndex": index,
                    "label": patientName,
                    "value": itemValue(source[index])
                })
            }
        }

        root.filteredItems = matches
        root.currentIndex = findSourceIndex(searchField.text)
        root.currentValue = root.currentIndex >= 0
                          ? itemValue(source[root.currentIndex])
                          : undefined
        resultList.currentIndex = matches.length > 0 ? 0 : -1

        if (openPopup && root.enabled)
            resultsPopup.open()
    }

    function choose(item) {
        if (!item)
            return

        searchField.text = item.label
        root.currentIndex = item.sourceIndex
        root.currentValue = item.value
        resultsPopup.close()
        searchField.forceActiveFocus()
        searchField.cursorPosition = searchField.text.length
        root.activated(item.sourceIndex, item.value)
    }

    function clearSelection() {
        searchField.text = ""
        root.currentIndex = -1
        root.currentValue = undefined
        root.filteredItems = []
        resultsPopup.close()
    }

    function selectValue(value) {
        var sourceIndex = findSourceIndex(value)
        searchField.text = sourceIndex >= 0
                         ? itemLabel(root.model[sourceIndex])
                         : String(value || "")
        root.currentIndex = sourceIndex
        root.currentValue = sourceIndex >= 0
                          ? itemValue(root.model[sourceIndex])
                          : undefined
        root.filteredItems = []
        resultsPopup.close()
    }

    onModelChanged: rebuildFilter(false)
    onEnabledChanged: {
        if (!enabled)
            resultsPopup.close()
    }

    AppTextField {
        id: searchField
        anchors.fill: parent
        rightPadding: 46
        inputMethodHints: Qt.ImhNoPredictiveText

        onTextEdited: root.rebuildFilter(true)

        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Down) {
                if (!resultsPopup.opened)
                    root.rebuildFilter(true)
                else if (root.filteredItems.length > 0)
                    resultList.incrementCurrentIndex()
                event.accepted = true
            } else if (event.key === Qt.Key_Up && resultsPopup.opened) {
                if (root.filteredItems.length > 0)
                    resultList.decrementCurrentIndex()
                event.accepted = true
            } else if ((event.key === Qt.Key_Return
                        || event.key === Qt.Key_Enter)
                       && resultsPopup.opened
                       && resultList.currentIndex >= 0) {
                root.choose(
                    root.filteredItems[resultList.currentIndex]
                )
                event.accepted = true
            } else if (event.key === Qt.Key_Escape
                       && resultsPopup.opened) {
                resultsPopup.close()
                event.accepted = true
            }
        }
    }

    Rectangle {
        id: dropDownArea
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 42
        color: dropDownMouse.containsMouse ? "#e8f6fd" : "transparent"
        radius: 8

        Label {
            anchors.centerIn: parent
            text: resultsPopup.opened ? "⌃" : "⌄"
            color: "#0b8fd3"
            font.pixelSize: 19
            font.weight: Font.DemiBold
        }

        MouseArea {
            id: dropDownMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                searchField.forceActiveFocus()
                root.rebuildFilter(true)
            }
        }
    }

    Popup {
        id: resultsPopup
        x: 0
        y: root.height + 4
        width: root.width
        height: Math.min(
            Math.max(1, root.filteredItems.length) * 42 + 2,
            root.maximumVisibleItems * 42 + 2
        )
        padding: 1
        closePolicy: Popup.CloseOnEscape
                     | Popup.CloseOnPressOutside
                     | Popup.CloseOnPressOutsideParent

        background: Rectangle {
            radius: 8
            color: "#ffffff"
            border.width: 1
            border.color: "#9ccbe5"
        }

        contentItem: Item {
            SmoothListView {
                id: resultList
                anchors.fill: parent
                clip: true
                model: root.filteredItems
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: ScrollBar {
                    policy: root.filteredItems.length
                            > root.maximumVisibleItems
                            ? ScrollBar.AlwaysOn
                            : ScrollBar.AsNeeded
                }

                delegate: Rectangle {
                    required property var modelData
                    required property int index

                    width: resultList.width
                    height: 42
                    color: {
                        if (resultMouse.containsMouse
                                || resultList.currentIndex === index)
                            return "#dff2fc"
                        return "#ffffff"
                    }

                    Label {
                        anchors.left: parent.left
                        anchors.leftMargin: 13
                        anchors.right: parent.right
                        anchors.rightMargin: 13
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        color: "#0f2747"
                        elide: Text.ElideRight
                        font.pixelSize: 13
                    }

                    MouseArea {
                        id: resultMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.choose(modelData)
                    }
                }
            }

            Label {
                visible: root.filteredItems.length === 0
                anchors.centerIn: parent
                text: "Nenhum paciente encontrado"
                color: "#6b7d96"
                font.pixelSize: 12
            }
        }
    }
}
