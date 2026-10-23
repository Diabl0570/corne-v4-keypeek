import Foundation
import IOKit.hid
import Testing
import CommandModeCore
@testable import CommandModeHelper

@Suite @MainActor
struct HelperRecoveryTests {
    private func observation(_ bundle: String = "com.openai.codex", vial: Bool = false) -> AppObservation {
        AppObservation(frontmost: bundle, runningBundleIDs: vial ? ["today.vial"] : [])
    }

    @Test func missingKeyboardReconnectsUsingCurrentForegroundAndStartsDisarmed() throws {
        var time: TimeInterval = 0
        var discoveries = 0
        let replacement = MockReportTransport()
        let runtime = HelperRuntime(observeApps: false, now: { time }, makeClient: {
            discoveries += 1
            if discoveries == 1 { throw CommandError.deviceNotFound }
            return CommandClient(transport: replacement)
        })
        runtime.tick(observation: observation())
        #expect(runtime.recovery == .waiting(deadline: 0.5, reason: .deviceNotFound))
        time = 0.49
        runtime.tick(observation: observation("com.google.Chrome"))
        #expect(discoveries == 1)
        time = 0.5
        runtime.tick(observation: observation("com.google.Chrome"))
        #expect(discoveries == 2)
        #expect(runtime.recovery == .active)
        #expect(runtime.client?.desiredLayer == 9)
        #expect(runtime.client?.state?.mode == .typing)
        #expect(!replacement.outputReports.contains { $0[3] == Opcode.context.rawValue })
    }

    @Test func persistentTimeoutReconnectsWithFreshTransportAndNeverRearmsAuto() throws {
        var time: TimeInterval = 0
        let original = MockReportTransport()
        let oldClient = CommandClient(transport: original, makeSession: { 41 })
        try oldClient.start()
        original.keyboardSelect(mode: .auto, layer: 7)
        original.transformReply = { _ in [] }
        let replacement = MockReportTransport()
        replacement.keyboardSelect(mode: .auto, layer: 8)
        var discoveries = 0
        let runtime = HelperRuntime(client: oldClient, observeApps: false, now: { time }, makeClient: {
            discoveries += 1
            return CommandClient(transport: replacement, makeSession: { 42 })
        })
        runtime.tick(observation: observation())
        #expect(runtime.recovery == .waiting(deadline: 0.5, reason: .timeout))
        #expect(!original.isOpen)
        #expect(original.outputReports.count == 5)
        time = 0.5
        runtime.tick(observation: observation("com.google.Chrome"))
        #expect(discoveries == 1)
        #expect(runtime.client?.transport === replacement)
        #expect(runtime.client?.session == 42)
        #expect(runtime.client?.desiredLayer == 9)
        #expect(replacement.mode == .manual)
        #expect(replacement.selectedLayer == 8)
        #expect(!replacement.outputReports.contains { $0[3] == Opcode.context.rawValue })
    }

    @Test func backoffEscalatesAcrossSuccessfulOpenFollowedByFailedPoll() {
        var time: TimeInterval = 0
        var discoveries = 0
        var healthy = false
        let runtime = HelperRuntime(observeApps: false, now: { time }, makeClient: {
            discoveries += 1
            let mock = MockReportTransport()
            var stateReplies = 0
            mock.transformReply = { reply in
                if reply[3] == Opcode.state.rawValue { stateReplies += 1 }
                return !healthy && stateReplies > 1 ? [] : [reply]
            }
            return CommandClient(transport: mock)
        })
        for (attempt, delay) in [0.5, 1.0, 2.0, 4.0, 8.0, 8.0].enumerated() {
            runtime.tick(observation: observation())
            #expect(discoveries == attempt + 1)
            #expect(runtime.failures == attempt + 1)
            #expect(runtime.recovery == .waiting(deadline: time + delay, reason: .timeout))
            time += delay - 0.01
            runtime.tick(observation: observation())
            #expect(discoveries == attempt + 1)
            time += 0.01
        }
        healthy = true
        runtime.tick(observation: observation())
        #expect(runtime.recovery == .active)
        #expect(runtime.failures == 0)
    }

    @Test func backoffStartsAfterSlowFailureRatherThanBeforeIO() {
        var time: TimeInterval = 0
        let runtime = HelperRuntime(observeApps: false, now: { time }, makeClient: {
            time += 0.8
            throw CommandError.timeout
        })
        runtime.tick(observation: observation())
        #expect(runtime.recovery == .waiting(deadline: 1.3, reason: .timeout))
    }

    @Test func vialBlocksDiscoveryThenWaitsQuietPeriodAndUserPauseStaysPaused() {
        var time: TimeInterval = 0
        var discoveries = 0
        let runtime = HelperRuntime(observeApps: false, now: { time }, makeClient: {
            discoveries += 1
            return CommandClient(transport: MockReportTransport())
        })
        runtime.tick(observation: observation(vial: true))
        #expect(runtime.recovery == .vialRunning)
        #expect(discoveries == 0)
        time = 5
        runtime.tick(observation: observation())
        #expect(runtime.recovery == .waiting(deadline: 7, reason: .status(.busyConfiguration)))
        time = 6.99
        runtime.tick(observation: observation())
        #expect(discoveries == 0)
        time = 7
        runtime.tick(observation: observation())
        #expect(discoveries == 1)
        #expect(runtime.recovery == .active)
        runtime.pause()
        time = 100
        runtime.tick(observation: observation(vial: true))
        runtime.tick(observation: observation())
        #expect(runtime.recovery == .userPaused)
        #expect(discoveries == 1)
        #expect(runtime.client?.phase == .paused(.user))
    }

    @Test func configurationTrafficWaitsTwoSecondsBeforeFreshDisarmedSession() throws {
        var time: TimeInterval = 0
        let old = MockReportTransport()
        let client = CommandClient(transport: old)
        try client.start()
        old.keyboardSelect(mode: .auto, layer: 7)
        old.configurationBusy = true
        let replacement = MockReportTransport()
        let runtime = HelperRuntime(client: client, observeApps: false, now: { time }, makeClient: {
            CommandClient(transport: replacement)
        })
        runtime.tick(observation: observation())
        #expect(runtime.recovery == .waiting(deadline: 2, reason: .status(.busyConfiguration)))
        #expect(!old.isOpen)
        time = 2
        runtime.tick(observation: observation())
        #expect(runtime.recovery == .active)
        #expect(runtime.client?.state?.mode == .typing)
    }

    @Test func incompatibleAndMalformedFailuresRemainBlockedUntilExplicitResume() {
        let errors: [CommandError] = [.incompatibleCapabilities, .unsupportedDevice, .malformedResponse,
                                     .readbackMismatch, .permissionDenied(-1), .multipleDevices,
                                     .transport("nested exchange"), .hidFailure(operation: "send", code: -1)]
        for error in errors {
            var time: TimeInterval = 0
            var attempts = 0
            let runtime = HelperRuntime(observeApps: false, now: { time }, makeClient: {
                attempts += 1
                throw error
            })
            runtime.tick(observation: observation())
            #expect(runtime.recovery == .blocked(error))
            time = 100
            runtime.tick(observation: observation())
            #expect(attempts == 1)
        }
    }

    @Test func onlyTransientNativeErrorsReconnect() {
        for code in [kIOReturnTimeout, kIOReturnNoDevice, kIOReturnNotResponding, kIOReturnOffline,
                     kIOReturnNotOpen, kIOReturnBusy, kIOReturnExclusiveAccess] {
            #expect(NativeHIDTransport.error(code, operation: "send").recovery == .reconnect)
        }
        for code in [kIOReturnBadArgument, kIOReturnUnsupported, kIOReturnNotPermitted,
                     kIOReturnNotPrivileged, kIOReturnError] {
            #expect(NativeHIDTransport.error(code, operation: "send").recovery == .stop)
        }
        #expect(CommandError.status(.wrongSession).recovery == .reconnect)
        #expect(CommandError.outputInFlight.recovery == .reconnect)
    }

    @Test func nativeNotReadyCompletionIsRecoverable() {
        let error = NativeHIDTransport.error(kIOReturnNotReady, operation: "completion")
        #expect(error == .hidUnavailable(operation: "completion", code: -536870184))
        #expect(error.recovery == .reconnect)
    }

    @Test func notReadyCompletionReconnectsWithFreshDisarmedSession() throws {
        var time: TimeInterval = 0
        let original = NotReadyTransport()
        let client = CommandClient(transport: original, makeSession: { 41 })
        try client.start()
        original.device.keyboardSelect(mode: .auto, layer: 7)
        original.failCompletion = true
        let replacement = MockReportTransport()
        replacement.keyboardSelect(mode: .auto, layer: 7)
        var discoveries = 0
        let runtime = HelperRuntime(client: client, observeApps: false, now: { time }, makeClient: {
            discoveries += 1
            return CommandClient(transport: replacement, makeSession: { 42 })
        })
        runtime.tick(observation: observation())
        #expect(runtime.recovery == .waiting(deadline: 0.5, reason: .hidUnavailable(
            operation: "completion", code: kIOReturnNotReady)))
        #expect(!original.device.isOpen)
        time = 0.49
        runtime.tick(observation: observation())
        #expect(discoveries == 0)
        time = 0.5
        runtime.tick(observation: observation("com.google.Chrome"))
        #expect(discoveries == 1)
        #expect(runtime.recovery == .active)
        #expect(runtime.client?.session == 42)
        #expect(runtime.client?.desiredLayer == 9)
        #expect(replacement.mode == .manual)
        #expect(replacement.selectedLayer == 7)
        #expect(!replacement.outputReports.contains { $0[3] == Opcode.context.rawValue })
    }
}

@MainActor
private final class NotReadyTransport: ReportTransport {
    let device = MockReportTransport()
    var failCompletion = false
    var descriptor: DeviceDescriptor { device.descriptor }
    func open() throws { try device.open() }
    func close() { device.close() }
    func send(_ report: [UInt8]) throws { try device.send(report) }
    func receive(timeout: TimeInterval) throws -> [UInt8]? {
        if failCompletion { throw NativeHIDTransport.error(kIOReturnNotReady, operation: "completion") }
        return try device.receive(timeout: timeout)
    }
}
