import Foundation
import Testing
@testable import CommandModeCore

@Suite @MainActor
struct CommandModeCoreTests {
    private func client(_ mock: MockReportTransport) -> CommandClient {
        var session: UInt32 = 40
        return CommandClient(transport: mock, makeSession: { session += 1; return session })
    }

    private func contextReports(_ mock: MockReportTransport) -> [[UInt8]] {
        mock.outputReports.filter { $0[3] == Opcode.context.rawValue }
    }

    private func expectError(_ expected: CommandError, _ operation: () throws -> Void) {
        do { try operation(); Issue.record("expected \(expected)") }
        catch { #expect(error as? CommandError == expected) }
    }

    @Test func exactRequestLayout() {
        let bytes = Request(opcode: .context, id: 0x04030201, session: 0x08070605,
                            epoch: 0x0C0B0A09, sequence: 0x100F0E0D, layer: 10).bytes
        #expect(bytes == [0xD3, 0x43, 1, 4, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
                          13, 14, 15, 16, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    }

    @Test func oldAndMismatchedDescriptorsProduceZeroOutputs() {
        let descriptors = [
            DeviceDescriptor(vendorID: 0x4653, productID: 4, usagePage: 0xFF60, usage: 0x61,
                             product: "Corne v4", release: 0x0410),
            DeviceDescriptor(vendorID: 0, productID: 4, usagePage: 0xFF60, usage: 0x61,
                             product: "Corne v4 CM1", release: 0x0411),
            DeviceDescriptor(vendorID: 0x4653, productID: 5, usagePage: 0xFF60, usage: 0x61,
                             product: "Corne v4 CM1", release: 0x0411),
            DeviceDescriptor(vendorID: 0x4653, productID: 4, usagePage: 0xFF60, usage: 0x60,
                             product: "Corne v4 CM1", release: 0x0411),
            DeviceDescriptor(vendorID: 0x4653, productID: 4, usagePage: 0xFF61, usage: 0x61,
                             product: "Corne v4 CM1", release: 0x0411),
        ]
        for descriptor in descriptors {
            let mock = MockReportTransport(descriptor: descriptor)
            let client = client(mock)
            expectError(.unsupportedDevice) { try client.start() }
            #expect(client.phase == .unsupported)
            #expect(mock.outputReports.isEmpty)
            #expect(!mock.isOpen)
            #expect(mock.openCount == 0)
        }
    }

    @Test func capabilityProbeDoesNotOpenSession() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.checkCapabilities()
        #expect(mock.outputReports.map { $0[3] } == [1])
        #expect(mock.session == 0)
        #expect(client.phase == .stopped)
        #expect(!mock.isOpen)
    }

    @Test func unchangedEchoIsNotAcknowledgement() {
        let mock = MockReportTransport()
        mock.transformReply = { reply in
            var echo = reply
            echo[1] = 0x43
            return [echo]
        }
        let client = client(mock)
        expectError(.timeout) { try client.start() }
        #expect(mock.outputReports.count == 2)
        #expect(mock.outputReports[0] == mock.outputReports[1])
        #expect(!mock.isOpen)
    }

    @Test func unrelatedAndOutOfOrderReportsAreIgnored() throws {
        let mock = MockReportTransport()
        mock.transformReply = { reply in
            var old = reply
            old.write(123_456, at: 4)
            var wrongOpcode = reply
            wrongOpcode[3] = reply[3] == 1 ? 3 : 1
            return [[0xC0, 0xA0], [0xFF, 2], [0xF1, 0, 0, 1], [0xFE, 0x02], old, wrongOpcode, reply]
        }
        let client = client(mock)
        try client.start()
        #expect(client.phase == .ready)
        #expect(mock.outputReports.map { $0[3] } == [1, 2, 3])
        #expect(mock.outputReports.allSatisfy { $0[0] == 0xD3 && $0[1] == 0x43 && $0.count == 32 })
    }

    @Test func malformedCapabilitiesNeverOpenSession() {
        for offset in [9, 10, 11, 12, 19, 20, 24, 28, 31] {
            let mock = MockReportTransport()
            mock.transformReply = { reply in
                var bad = reply
                bad[offset] ^= 1
                return [bad]
            }
            let client = client(mock)
            expectError(.incompatibleCapabilities) { try client.start() }
            #expect(mock.outputReports.count == 1)
            #expect(mock.session == 0)
        }
    }

    @Test func preRaycastRegistryCannotOpenSession() {
        let mock = MockReportTransport()
        mock.transformReply = { reply in
            var old = reply
            old.write(0x36FE6906, at: 20)
            return [old]
        }
        expectError(.incompatibleCapabilities) { try client(mock).start() }
        #expect(mock.outputReports.map { $0[3] } == [Opcode.capabilities.rawValue])
        #expect(mock.session == 0)
        #expect(!mock.isOpen)
    }

    @Test func exactFrameSizeAndVersionRequired() {
        for mutation in 0..<4 {
            let mock = MockReportTransport()
            mock.transformReply = { reply in
                var bad = reply
                switch mutation {
                case 0: bad.removeLast()
                case 1: bad.append(0)
                case 2: bad[2] = 2
                default: bad[8] = 255
                }
                return [bad]
            }
            expectError(.malformedResponse) { try client(mock).start() }
            #expect(mock.outputReports.count == 1)
        }
    }

    @Test func malformedStateFailsClosed() {
        for offset in [9, 10, 11, 26, 27, 28] {
            let mock = MockReportTransport()
            mock.transformReply = { reply in
                guard reply[3] != 1 else { return [reply] }
                var bad = reply
                bad[offset] = 255
                return [bad]
            }
            let client = client(mock)
            expectError(.malformedResponse) { try client.start() }
            #expect(!mock.isOpen)
        }
    }

    @Test func typingAndManualModesIgnoreFocus() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        client.observe(bundleID: "com.openai.codex")
        try client.poll()
        #expect(mock.mode == .typing)
        #expect(contextReports(mock).isEmpty)
        mock.keyboardSelect(mode: .manual, layer: 11)
        client.observe(bundleID: "com.google.Chrome")
        try client.poll()
        #expect(mock.selectedLayer == 11)
        #expect(contextReports(mock).isEmpty)
    }

    @Test func registryMapsInstalledAppsAndTransientOverlays() {
        let client = client(MockReportTransport())
        let cases: [(String, UInt8)] = [
            ("com.openai.codex", 7), ("com.anthropic.claudefordesktop", 8),
            ("com.google.Chrome", 9), ("com.openai.atlas", 9), ("com.apple.Safari", 9),
            ("com.microsoft.edgemac", 9), ("com.todesktop.230313mzl4w4u92", 10),
            ("com.microsoft.VSCode", 10), ("com.raycast.macos", 0), ("unknown.app", 6),
        ]
        for (bundle, expected) in cases {
            client.observe(bundleID: bundle)
            #expect(client.desiredLayer == expected)
        }
        client.observe(bundleID: "com.openai.codex")
        for bundle in ["dev.srwi.keypeek", "com.apple.dock"] {
            client.observe(bundleID: bundle)
            #expect(client.desiredLayer == 7)
        }
        client.observe(bundleID: nil)
        #expect(client.desiredLayer == 7)
        #expect((UInt8(0)...15).filter(CommandRegistry.allowsAutomaticLayer) == [0, 6, 7, 8, 9, 10])
        #expect(!CommandRegistry.allowsAutomaticLayer(255))
    }

    @Test func raycastTypesAndReturnsToAppWithoutDisarmingAuto() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 7)
        let epoch = mock.epoch
        for (bundle, layer) in [("com.openai.codex", UInt8(7)), ("com.raycast.macos", 0),
                                ("com.anthropic.claudefordesktop", 8)] {
            client.observe(bundleID: bundle)
            try client.poll()
            #expect(mock.selectedLayer == layer)
            #expect(client.lastAcknowledgedLayer == layer)
            #expect(mock.mode == .auto)
            #expect(mock.epoch == epoch)
            #expect(client.state?.appliedMask == (layer == 0 ? 0 : UInt16(1) << layer))
        }
        #expect(contextReports(mock).map { $0[20] } == [7, 0, 8])
    }

    @Test func raycastEntryAndExitWaitForKeyRelease() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 7)
        for (bundle, before, after) in [("com.raycast.macos", UInt8(7), UInt8(0)),
                                       ("com.openai.codex", 0, 7)] {
            mock.keysHeld = true
            client.observe(bundleID: bundle)
            try client.poll()
            #expect(mock.selectedLayer == before)
            #expect(client.state?.deferred == true)
            mock.keysHeld = false
            try client.poll()
            #expect(mock.selectedLayer == after)
            #expect(client.state?.deferred == false)
            #expect(mock.mode == .auto)
        }
    }

    @Test func homeAndRestartDuringRaycastCannotRestoreCommandMode() throws {
        for home in [true, false] {
            let mock = MockReportTransport()
            let client = client(mock)
            try client.start()
            mock.keyboardSelect(mode: .auto, layer: 7)
            client.observe(bundleID: "com.raycast.macos")
            try client.poll()
            if home { mock.keyboardSelect(mode: .typing, layer: 0) }
            else { client.pause(); try client.start() }
            let count = contextReports(mock).count
            client.observe(bundleID: "com.openai.codex")
            try client.poll()
            #expect(mock.mode == .typing)
            #expect(mock.selectedLayer == 0)
            #expect(contextReports(mock).count == count)
        }
    }

    @Test func autoSendsOnlyNewestContextAndReadsItBack() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 6)
        client.observe(bundleID: "com.openai.codex")
        client.observe(bundleID: "com.google.Chrome")
        client.observe(bundleID: "com.microsoft.VSCode")
        try client.poll()
        #expect(mock.selectedLayer == 10)
        #expect(client.lastAcknowledgedLayer == 10)
        let report = try #require(contextReports(mock).first)
        #expect(report[20] == 10)
        #expect(report.read32(at: 8) == client.session)
        #expect(report.read32(at: 12) == mock.epoch)
        #expect(report.read32(at: 16) == 1)
        try client.poll()
        #expect(contextReports(mock).count == 1)
        #expect(mock.outputReports.suffix(3).map { $0[3] } == [4, 3, 3])
    }

    @Test func unknownAppFallsBackToGenericOnlyInAuto() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 8)
        client.observe(bundleID: "unknown.app")
        try client.poll()
        #expect(mock.selectedLayer == 6)
    }

    @Test func pickerSuspendsContextUntilFreshEpoch() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 6, picker: true)
        client.observe(bundleID: "com.openai.codex")
        try client.poll()
        #expect(contextReports(mock).isEmpty)
        mock.keyboardSelect(mode: .auto, layer: 6)
        try client.poll()
        #expect(mock.selectedLayer == 7)
    }

    @Test func homeBetweenPollAndContextCannotRearm() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 6)
        mock.beforeRequest = { opcode in
            if opcode == .context { mock.keyboardSelect(mode: .typing, layer: 0) }
        }
        client.observe(bundleID: "com.openai.codex")
        try client.poll()
        #expect(mock.mode == .typing)
        #expect(client.state?.mode == .typing)
        try client.poll()
        #expect(contextReports(mock).count == 1)
        #expect(mock.selectedLayer == 0)
    }

    @Test func deferredContextWaitsForReadbackAndCoalescesNewFocus() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 6)
        mock.keysHeld = true
        client.observe(bundleID: "com.openai.codex")
        try client.poll()
        #expect(client.state?.deferred == true)
        #expect(mock.selectedLayer == 6)
        try client.poll()
        #expect(contextReports(mock).count == 1)
        client.observe(bundleID: "com.google.Chrome")
        try client.poll()
        #expect(contextReports(mock).count == 2)
        #expect(contextReports(mock).last?.read32(at: 16) == 2)
        mock.keysHeld = false
        try client.poll()
        #expect(mock.selectedLayer == 9)
        #expect(client.state?.deferred == false)
        #expect(contextReports(mock).count == 2)
    }

    @Test func acknowledgementRequiresIndependentReadback() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 6)
        var contextSent = false
        mock.beforeRequest = { opcode in
            if opcode == .context { contextSent = true }
        }
        mock.transformReply = { reply in
            var reply = reply
            if contextSent, reply[3] == Opcode.state.rawValue { reply[10] = 6 }
            return [reply]
        }
        client.observe(bundleID: "com.openai.codex")
        expectError(.readbackMismatch) { try client.poll() }
        #expect(!mock.isOpen)
    }

    @Test func restartAndResumeAlwaysDisarmFirmware() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        let originalSession = client.session
        mock.keyboardSelect(mode: .auto, layer: 8)
        client.pause()
        #expect(client.phase == .paused(.user))
        #expect(mock.mode == .manual)
        #expect(mock.session == 0)
        try client.start()
        #expect(client.session != originalSession)
        #expect(mock.mode == .manual)
        #expect(mock.selectedLayer == 8)
        client.observe(bundleID: "com.openai.codex")
        try client.poll()
        #expect(contextReports(mock).isEmpty)
        let secondClient = self.client(mock)
        try secondClient.start()
        #expect(mock.mode != .auto)
    }

    @Test func reusedOrZeroSessionFailsBeforeOutput() {
        for session in [UInt32(0)] {
            let mock = MockReportTransport()
            let client = CommandClient(transport: mock, makeSession: { session })
            #expect(throws: (any Error).self) { try client.start() }
            #expect(mock.outputReports.isEmpty)
        }
    }

    @Test func reusedSessionIsRejectedOnResume() throws {
        let mock = MockReportTransport()
        let client = CommandClient(transport: mock, makeSession: { 41 })
        try client.start()
        client.pause()
        let count = mock.outputReports.count
        #expect(throws: (any Error).self) { try client.start() }
        #expect(mock.outputReports.count == count)
        #expect(!mock.isOpen)
    }

    @Test func missingAcknowledgementAndReportFloodAreBounded() {
        for flood in [false, true] {
            let mock = MockReportTransport()
            mock.transformReply = { _ in flood ? Array(repeating: [0xC0], count: 65) : [] }
            let client = client(mock)
            expectError(.timeout) { try client.start() }
            #expect(mock.outputReports.count == 2)
            #expect(mock.outputReports[0] == mock.outputReports[1])
            #expect(client.acknowledgementRetries == 1)
            #expect(!mock.isOpen)
        }
    }

    @Test func lostReplyRetriesIdenticalRequestWithoutReopeningOrDisarming() throws {
        for opcode in [Opcode.state, .context] {
            let mock = MockReportTransport()
            let client = client(mock)
            try client.start()
            let originalSession = client.session
            mock.keyboardSelect(mode: .auto, layer: 6)
            var dropped = false
            mock.transformReply = { reply in
                if !dropped, reply[3] == opcode.rawValue { dropped = true; return [] }
                return [reply]
            }
            client.observe(bundleID: "com.openai.codex")
            try client.poll()
            #expect(dropped)
            #expect(client.phase == .ready)
            #expect(client.session == originalSession)
            #expect(mock.openCount == 1)
            #expect(mock.mode == .auto)
            #expect(mock.selectedLayer == 7)
            #expect(client.state?.selectedLayer == 7)
            #expect(client.acknowledgementRetries == 1)
            let retry = Array(mock.outputReports.dropFirst(3).filter { $0[3] == opcode.rawValue }.prefix(2))
            #expect(retry.count == 2)
            #expect(retry[0] == retry[1])
            #expect(mock.outputReports.last?[3] == Opcode.state.rawValue)
        }
    }

    @Test func homeDuringLostReplyStillDisarmsBeforeRetry() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 6)
        var dropped = false
        mock.transformReply = { reply in
            if !dropped, reply[3] == Opcode.context.rawValue {
                dropped = true
                mock.keyboardSelect(mode: .typing, layer: 0)
                return []
            }
            return [reply]
        }
        client.observe(bundleID: "com.openai.codex")
        try client.poll()
        #expect(client.phase == .ready)
        #expect(client.state?.mode == .typing)
        #expect(client.lastAcknowledgedLayer == nil)
        #expect(mock.selectedLayer == 0)
        #expect(contextReports(mock).count == 2)
    }

    @Test func successfulReplyWithContradictorySessionIsTerminal() throws {
        for inactive in [false, true] {
            let mock = MockReportTransport()
            let client = client(mock)
            try client.start()
            mock.transformReply = { reply in
                var reply = reply
                if inactive { reply[11] &= ~8; reply.write(0, at: 12) }
                else { reply.write(999, at: 12) }
                return [reply]
            }
            expectError(.readbackMismatch) { try client.poll() }
            #expect(client.phase == .failed(.readbackMismatch))
            #expect(CommandError.readbackMismatch.recovery == .stop)
            #expect(mock.outputReports.count == 4)
        }
    }

    @Test func pendingOutputCannotStartParallelRetry() {
        let transport = PendingOutputTransport()
        let client = CommandClient(transport: transport)
        expectError(.outputInFlight) { try client.start() }
        #expect(transport.sendAttempts == 2)
        #expect(transport.outputsStarted == 1)
        #expect(transport.closed)
        #expect(client.phase == .failed(.outputInFlight))
    }

    @Test func homeAfterAcknowledgementWinsOverReadback() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 6)
        var contextSent = false
        mock.beforeRequest = { opcode in
            if opcode == .context { contextSent = true }
            else if opcode == .state, contextSent {
                contextSent = false
                mock.keyboardSelect(mode: .typing, layer: 0)
            }
        }
        client.observe(bundleID: "com.openai.codex")
        try client.poll()
        #expect(client.state?.mode == .typing)
        #expect(client.lastAcknowledgedLayer == nil)
        try client.poll()
        #expect(contextReports(mock).count == 1)
    }

    @Test func disconnectRequiresExplicitFreshSession() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 7)
        mock.connected = false
        expectError(.disconnected) { try client.poll() }
        let count = mock.outputReports.count
        mock.connected = true
        try client.poll()
        #expect(mock.outputReports.count == count)
        try client.start()
        #expect(mock.mode == .manual)
        #expect(mock.selectedLayer == 7)
    }

    @Test func vialProcessPausesEvenInBackgroundAndNeverAutoResumes() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 7)
        client.observeApplications(frontmost: "com.openai.codex", runningBundleIDs: ["today.vial"])
        #expect(client.phase == .paused(.vialRunning))
        #expect(!mock.isOpen)
        #expect(mock.outputReports.last?[3] == Opcode.close.rawValue)
        let count = mock.outputReports.count
        client.observeApplications(frontmost: "com.openai.codex", runningBundleIDs: [])
        try client.poll()
        #expect(mock.outputReports.count == count)
        #expect(client.phase == .paused(.vialRunning))
        try client.start()
        #expect(mock.mode != .auto)
    }

    @Test func vialAlreadyRunningPreventsOpeningTheDevice() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        client.observeApplications(frontmost: "com.openai.codex", runningBundleIDs: ["today.vial"])
        try client.start()
        #expect(client.phase == .paused(.vialRunning))
        #expect(mock.openCount == 0)
        #expect(mock.outputReports.isEmpty)
    }

    @Test func busyConfigurationReleasesHandleAndRequiresManualResume() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 7)
        mock.configurationBusy = true
        expectError(.status(.busyConfiguration)) { try client.poll() }
        #expect(client.phase == .paused(.configurationTraffic))
        #expect(!mock.isOpen)
        #expect(mock.mode == .manual)
        mock.configurationBusy = false
        let count = mock.outputReports.count
        try client.poll()
        #expect(mock.outputReports.count == count)
        try client.start()
        #expect(mock.mode == .manual)
    }

    @Test func leaseExpiryDisarmsAndHelperFailsClosed() throws {
        var now: TimeInterval = 10
        let mock = MockReportTransport(now: { now })
        let client = client(mock)
        try client.start()
        mock.keyboardSelect(mode: .auto, layer: 7)
        now += 2.01
        expectError(.status(.wrongSession)) { try client.poll() }
        #expect(mock.mode == .manual)
        #expect(!mock.isOpen)
    }

    @Test func lifecycleCloseIsIdempotentAndNeverSendsKeyPeek() throws {
        let mock = MockReportTransport()
        let client = client(mock)
        try client.start()
        client.stop()
        let count = mock.outputReports.count
        client.stop()
        #expect(mock.outputReports.count == count)
        #expect(client.phase == .stopped)
        #expect(mock.session == 0)
        #expect(mock.outputReports.allSatisfy { $0[0] == 0xD3 && $0[1] == 0x43 })
    }
}

@MainActor
private final class PendingOutputTransport: ReportTransport {
    let descriptor = DeviceDescriptor.commandMode
    var sendAttempts = 0
    var outputsStarted = 0
    var closed = false
    func open() throws {}
    func close() { closed = true }
    func send(_ report: [UInt8]) throws {
        sendAttempts += 1
        guard outputsStarted == 0 else { throw CommandError.outputInFlight }
        outputsStarted += 1
    }
    func receive(timeout: TimeInterval) throws -> [UInt8]? { nil }
}
