import QtQuick

ListView {
    id: root

    property real mouseWheelDistance: 96
    property int mouseWheelDuration: 140

    boundsBehavior: Flickable.StopAtBounds
    flickDeceleration: 2400
    maximumFlickVelocity: 3600

    function boundedY(value) {
        const minimum = originY
        const maximum = Math.max(
            minimum,
            minimum + contentHeight - height
        )
        return Math.max(minimum, Math.min(maximum, value))
    }

    WheelHandler {
        target: null
        onWheel: function(event) {
            if (root.contentHeight <= root.height)
                return

            const pixelY = event.pixelDelta.y
            if (pixelY !== 0) {
                wheelAnimation.stop()
                root.contentY = root.boundedY(root.contentY - pixelY)
                event.accepted = true
                return
            }

            const steps = event.angleDelta.y / 120
            const currentTarget = wheelAnimation.running
                                ? wheelAnimation.to : root.contentY
            wheelAnimation.stop()
            wheelAnimation.from = root.contentY
            wheelAnimation.to = root.boundedY(
                currentTarget - steps * root.mouseWheelDistance
            )
            wheelAnimation.start()
            event.accepted = true
        }
    }

    NumberAnimation {
        id: wheelAnimation
        target: root
        property: "contentY"
        duration: root.mouseWheelDuration
        easing.type: Easing.OutCubic
    }
}
