import QtQuick
import QtQuick.Controls

ScrollView {
    id: root

    property real mouseWheelDistance: 112
    property int mouseWheelDuration: 150

    clip: true

    Component.onCompleted: {
        if (contentItem) {
            contentItem.boundsBehavior = Flickable.StopAtBounds
            contentItem.flickDeceleration = 2400
            contentItem.maximumFlickVelocity = 3600
        }
    }

    function boundedY(value) {
        const flick = contentItem
        if (!flick)
            return 0
        const minimum = flick.originY
        const maximum = Math.max(
            minimum,
            minimum + flick.contentHeight - flick.height
        )
        return Math.max(minimum, Math.min(maximum, value))
    }

    function scrollWithWheel(event) {
        const flick = contentItem
        if (!flick || flick.contentHeight <= flick.height)
            return

        const pixelY = event.pixelDelta.y
        if (pixelY !== 0) {
            wheelAnimation.stop()
            flick.contentY = boundedY(flick.contentY - pixelY)
            event.accepted = true
            return
        }

        const steps = event.angleDelta.y / 120
        const currentTarget = wheelAnimation.running
                            ? wheelAnimation.to : flick.contentY
        wheelAnimation.stop()
        wheelAnimation.from = flick.contentY
        wheelAnimation.to = boundedY(
            currentTarget - steps * mouseWheelDistance
        )
        wheelAnimation.start()
        event.accepted = true
    }

    WheelHandler {
        id: wheelHandler
        target: null
        onWheel: function(event) {
            root.scrollWithWheel(event)
        }
    }

    NumberAnimation {
        id: wheelAnimation
        target: root.contentItem
        property: "contentY"
        duration: root.mouseWheelDuration
        easing.type: Easing.OutCubic
    }
}
