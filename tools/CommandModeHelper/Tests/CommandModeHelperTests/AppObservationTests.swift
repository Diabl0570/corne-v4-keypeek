import Testing
import CommandModeCore
@testable import CommandModeHelper

@Suite @MainActor
struct AppObservationTests {
    private func observation(_ frontmost: String?, panel: Bool = false) -> AppObservation {
        AppObservation(frontmost: frontmost, runningBundleIDs: ["com.raycast.macos"], raycastPanelVisible: panel)
    }

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

    @Test func dismissalDuringTransientFocusRestoresLatestUnderlyingApp() throws {
        for transient in [nil, "dev.srwi.keypeek", "com.apple.dock"] as [String?] {
            let device = MockReportTransport()
            let client = CommandClient(transport: device)
            try client.start()
            device.keyboardSelect(mode: .auto, layer: 7)
            observation("com.openai.codex", panel: true).apply(to: client)
            try client.poll()
            #expect(device.selectedLayer == 0)
            observation("com.google.Chrome", panel: true).apply(to: client)
            #expect(client.observedBundleID == "com.google.Chrome")
            #expect(client.desiredLayer == 0)
            observation(transient).apply(to: client)
            try client.poll()
            #expect(client.desiredLayer == 9)
            #expect(device.selectedLayer == 9)
            #expect(device.mode == .auto)
        }
    }

    @Test func frontmostRaycastSettingsDoesNotReplaceUnderlyingContext() throws {
        let device = MockReportTransport()
        let client = CommandClient(transport: device)
        try client.start()
        device.keyboardSelect(mode: .auto, layer: 7)
        observation("com.openai.codex").apply(to: client)
        observation("com.raycast.macos").apply(to: client)
        try client.poll()
        #expect(client.observedBundleID == "com.openai.codex")
        #expect(device.selectedLayer == 0)
        observation("dev.srwi.keypeek").apply(to: client)
        try client.poll()
        #expect(device.selectedLayer == 7)
    }

    @Test func coldStartRaycastThenTransientFallsBackToGeneric() throws {
        let device = MockReportTransport()
        let client = CommandClient(transport: device)
        try client.start()
        device.keyboardSelect(mode: .auto, layer: 6)
        observation("com.raycast.macos", panel: true).apply(to: client)
        try client.poll()
        #expect(client.observedBundleID == nil)
        #expect(device.selectedLayer == 0)
        observation(nil).apply(to: client)
        try client.poll()
        #expect(client.desiredLayer == 6)
        #expect(device.selectedLayer == 6)
    }

    @Test func panelCannotOverrideTypingManualOrPicker() throws {
        for (mode, layer, picker) in [(FirmwareMode.typing, UInt8(0), false),
                                      (.manual, 11, false), (.auto, 7, true)] {
            let device = MockReportTransport()
            let client = CommandClient(transport: device)
            try client.start()
            device.keyboardSelect(mode: mode, layer: layer, picker: picker)
            observation("com.openai.codex", panel: true).apply(to: client)
            try client.poll()
            #expect(device.mode == mode)
            #expect(device.selectedLayer == layer)
            #expect(!device.outputReports.contains { $0[3] == Opcode.context.rawValue })
        }
    }

    @Test func homeDuringPanelPreventsCommandRestoration() throws {
        let device = MockReportTransport()
        let client = CommandClient(transport: device)
        try client.start()
        device.keyboardSelect(mode: .auto, layer: 7)
        observation("com.openai.codex", panel: true).apply(to: client)
        try client.poll()
        device.keyboardSelect(mode: .typing, layer: 0)
        observation("com.openai.codex").apply(to: client)
        try client.poll()
        #expect(client.desiredLayer == 7)
        #expect(device.mode == .typing)
        #expect(device.selectedLayer == 0)
    }

    @Test func reconnectDuringPanelCannotRearmAuto() throws {
        var time = 0.0
        let original = MockReportTransport()
        let client = CommandClient(transport: original, makeSession: { 41 })
        try client.start()
        original.keyboardSelect(mode: .auto, layer: 7)
        observation("com.openai.codex", panel: true).apply(to: client)
        try client.poll()
        original.connected = false
        let replacement = MockReportTransport()
        replacement.keyboardSelect(mode: .auto, layer: 7)
        let runtime = HelperRuntime(client: client, observeApps: false, now: { time }, makeClient: {
            CommandClient(transport: replacement, makeSession: { 42 })
        })
        runtime.tick(observation: observation("com.openai.codex", panel: true))
        time = 0.5
        runtime.tick(observation: observation("com.openai.codex", panel: true))
        #expect(runtime.recovery == .active)
        #expect(runtime.client?.desiredLayer == 0)
        #expect(replacement.mode == .manual)
        #expect(replacement.selectedLayer == 7)
        runtime.tick(observation: observation("dev.srwi.keypeek"))
        #expect(runtime.client?.desiredLayer == 7)
        #expect(!replacement.outputReports.contains { $0[3] == Opcode.context.rawValue })
    }

    @Test func panelObservationStillPausesForVial() throws {
        let device = MockReportTransport()
        let client = CommandClient(transport: device)
        try client.start()
        AppObservation(frontmost: "com.openai.codex", runningBundleIDs: ["today.vial", "com.raycast.macos"],
                       raycastPanelVisible: true).apply(to: client)
        #expect(client.phase == .paused(.vialRunning))
        #expect(!device.isOpen)
    }

    @Test func diagnosticsDistinguishPanelFromRawForeground() {
        let closed = observation("com.anthropic.claudefordesktop")
        let open = observation("com.anthropic.claudefordesktop", panel: true)
        #expect(closed.diagnosticDescription != open.diagnosticDescription)
        #expect(open.diagnosticDescription.contains("bundle=com.anthropic.claudefordesktop"))
        #expect(open.diagnosticDescription.contains("raycastPanel=true"))
    }
}
