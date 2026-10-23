import Testing
import CommandModeCore
@testable import CommandModeHelper

@Suite @MainActor
struct AppObservationTests {
    @Test func visibleRaycastPanelOverridesUnchangedForeground() throws {
        let device = MockReportTransport()
        let client = CommandClient(transport: device)
        try client.start()
        device.keyboardSelect(mode: .auto, layer: 7)
        AppObservation(frontmost: "com.openai.codex", runningBundleIDs: ["com.raycast.macos"],
                       raycastPanelVisible: false).apply(to: client)
        try client.poll()
        #expect(device.selectedLayer == 7)
        AppObservation(frontmost: "com.openai.codex", runningBundleIDs: ["com.raycast.macos"],
                       raycastPanelVisible: true).apply(to: client)
        try client.poll()
        #expect(client.observedBundleID == "com.openai.codex")
        #expect(client.desiredLayer == 0)
        #expect(device.selectedLayer == 0)
        #expect(device.mode == .auto)
    }
}
