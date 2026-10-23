import AppKit
import Foundation
import Testing
import CommandModeCore
@testable import CommandModeHelper

@Suite @MainActor
struct HelperRuntimeTests {
    @Test func appActivationCoalescesAndStopsObserving() {
        let center = NotificationCenter()
        let signal = AppActivationSignal(center: center)
        #expect(!signal.pending)
        for _ in 0..<3 { center.post(name: NSWorkspace.didActivateApplicationNotification, object: nil) }
        #expect(signal.pending)
        signal.clear()
        #expect(!signal.pending)
        center.post(name: NSWorkspace.didActivateApplicationNotification, object: nil)
        #expect(signal.pending)
        signal.stop()
        signal.stop()
        center.post(name: NSWorkspace.didActivateApplicationNotification, object: nil)
        #expect(!signal.pending)
    }

    @Test func callbackCleanupUsesOriginalContextAcrossRepeatedOpenClose() throws {
        let context = try #require(UnsafeMutableRawPointer(bitPattern: 0x1234))
        var events: [String] = []
        var contexts: [UInt] = []
        func record(_ event: String, _ pointer: UnsafeMutableRawPointer) {
            events.append(event)
            contexts.append(UInt(bitPattern: pointer))
        }
        let registration = HIDCallbackRegistration(
            context: context,
            registerInput: { record("input+", $0) },
            registerRemoval: { record("removal+", $0) },
            unregisterInput: { record("input-", $0) },
            unregisterRemoval: { record("removal-", $0) }
        )
        for _ in 0..<3 {
            registration.install()
            registration.install()
            registration.remove()
            registration.remove()
        }
        #expect(events == Array(repeating: ["input+", "removal+", "input-", "removal-"], count: 3).flatMap { $0 })
        #expect(contexts == Array(repeating: UInt(bitPattern: context), count: 12))
    }

    @Test func explicitResumeDiscoversReplacementTransportAndStartsDisarmed() throws {
        let removed = MockReportTransport()
        let oldClient = CommandClient(transport: removed)
        try oldClient.start()
        removed.keyboardSelect(mode: .auto, layer: 8)
        removed.connected = false
        #expect(throws: CommandError.disconnected) { try oldClient.poll() }

        let replacement = MockReportTransport()
        replacement.keyboardSelect(mode: .auto, layer: 7)
        var discoveries = 0
        let runtime = HelperRuntime(client: oldClient, observeApps: false, makeClient: {
            discoveries += 1
            return CommandClient(transport: replacement)
        })
        #expect(discoveries == 0)
        try runtime.resume()
        #expect(discoveries == 1)
        #expect(runtime.client !== oldClient)
        #expect(runtime.client?.transport === replacement)
        #expect(replacement.mode == .manual)
        #expect(replacement.selectedLayer == 7)
        #expect(!removed.isOpen)
    }

    @Test func replacementOldFirmwareHasZeroOutputReports() throws {
        let removed = MockReportTransport()
        let oldClient = CommandClient(transport: removed)
        try oldClient.start()
        removed.connected = false
        let replacement = MockReportTransport(descriptor: DeviceDescriptor(
            vendorID: 0x4653, productID: 4, usagePage: 0xFF60, usage: 0x61,
            product: "Corne v4", release: 0x0410
        ))
        let runtime = HelperRuntime(client: oldClient, observeApps: false, makeClient: {
            CommandClient(transport: replacement)
        })
        #expect(throws: CommandError.unsupportedDevice) { try runtime.resume() }
        #expect(runtime.recovery == .blocked(.unsupportedDevice))
        #expect(replacement.outputReports.isEmpty)
        #expect(!replacement.isOpen)
        #expect(replacement.openCount == 0)
    }
}
