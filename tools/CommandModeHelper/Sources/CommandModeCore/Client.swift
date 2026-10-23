import Foundation

@MainActor
public protocol ReportTransport: AnyObject {
    var descriptor: DeviceDescriptor { get }
    func open() throws
    func close()
    func send(_ report: [UInt8]) throws
    func receive(timeout: TimeInterval) throws -> [UInt8]?
}

public enum PauseReason: String, Equatable, Sendable {
    case user
    case vialRunning
    case configurationTraffic
}

public enum ClientPhase: Equatable, Sendable, CustomStringConvertible {
    case stopped
    case connecting
    case ready
    case paused(PauseReason)
    case unsupported
    case failed(String)

    public var description: String {
        switch self {
        case .stopped: "stopped"
        case .connecting: "connecting"
        case .ready: "ready"
        case .paused(let reason): "paused(\(reason.rawValue))"
        case .unsupported: "unsupported"
        case .failed(let message): "failed(\(message))"
        }
    }
}

@MainActor
public final class CommandClient {
    public private(set) var phase: ClientPhase = .stopped
    public private(set) var state: FirmwareState?
    public private(set) var observedBundleID: String?
    public private(set) var desiredLayer: UInt8 = 6
    public private(set) var lastAcknowledgedLayer: UInt8?
    public private(set) var session: UInt32 = 0
    public let transport: any ReportTransport
    private var requestID: UInt32 = 0
    private var sequence: UInt32 = 0
    private var deliveredContext: ContextReceipt?
    private var vialRunning = false
    private let makeSession: () -> UInt32
    private let timeout: TimeInterval
    private var inFlight = false
    private var previousSession: UInt32 = 0

    private struct ContextReceipt {
        let epoch: UInt32
        let layer: UInt8
    }

    public init(transport: any ReportTransport, timeout: TimeInterval = 0.4,
                makeSession: @escaping () -> UInt32 = { UInt32.random(in: 1...UInt32.max) }) {
        self.transport = transport
        self.timeout = timeout
        self.makeSession = makeSession
    }

    public func checkCapabilities() throws {
        guard phase == .stopped else { throw CommandError.transport("stop the client before probing") }
        guard transport.descriptor.supported else {
            phase = .unsupported
            throw CommandError.unsupportedDevice
        }
        try transport.open()
        defer { transport.close() }
        try requireOK(exchange(.capabilities, session: 0))
    }

    public func start() throws {
        if phase == .ready { stop() }
        guard !vialRunning else { phase = .paused(.vialRunning); return }
        guard transport.descriptor.supported else {
            phase = .unsupported
            throw CommandError.unsupportedDevice
        }
        phase = .connecting
        state = nil
        deliveredContext = nil
        lastAcknowledgedLayer = nil
        sequence = 0
        requestID = 0
        session = makeSession()
        guard session != 0, session != previousSession else {
            try fail(CommandError.transport("session generator must produce a fresh nonzero session"))
        }
        previousSession = session
        do {
            try transport.open()
            let capabilities = try exchange(.capabilities, session: 0)
            try requireOK(capabilities)
            let opened = try exchange(.open)
            try requireOK(opened)
            guard let openedState = opened.state,
                  openedState.session == session, openedState.sessionActive,
                  openedState.mode != .auto else { throw CommandError.readbackMismatch }
            let readback = try exchange(.state)
            try requireOK(readback)
            guard let snapshot = readback.state, snapshot.session == session,
                  snapshot.sessionActive, snapshot.mode != .auto else {
                throw CommandError.readbackMismatch
            }
            state = snapshot
            phase = .ready
        } catch { try fail(error) }
    }

    public func observe(bundleID: String?) {
        guard let bundleID, !CommandRegistry.transientBundleIDs.contains(bundleID) else { return }
        observedBundleID = bundleID
        desiredLayer = CommandRegistry.layer(forBundleID: bundleID)
    }

    public func observeApplications(frontmost: String?, runningBundleIDs: Set<String>) {
        vialRunning = runningBundleIDs.contains(CommandRegistry.configuratorBundleID)
        if vialRunning, phase == .ready || phase == .connecting { pause(.vialRunning) }
        observe(bundleID: frontmost)
    }

    public func poll() throws {
        guard phase == .ready else { return }
        do {
            let response = try exchange(.state)
            try requireOK(response)
            guard let snapshot = response.state, snapshot.session == session,
                  snapshot.sessionActive else { throw CommandError.readbackMismatch }
            state = snapshot
            guard snapshot.mode == .auto, !snapshot.picker else {
                deliveredContext = nil
                lastAcknowledgedLayer = nil
                return
            }
            if let deliveredContext, deliveredContext.epoch == snapshot.epoch,
               deliveredContext.layer == desiredLayer {
                guard snapshot.deferred || snapshot.selectedLayer == desiredLayer else {
                    throw CommandError.readbackMismatch
                }
                return
            }
            guard CommandRegistry.allowsAutomaticLayer(desiredLayer) else { throw CommandError.readbackMismatch }
            guard sequence < UInt32.max else { throw CommandError.counterExhausted }
            sequence += 1
            let acknowledgement = try exchange(.context, epoch: snapshot.epoch,
                                                sequence: sequence, layer: desiredLayer)
            if [.staleEpoch, .staleSequence, .disarmed].contains(acknowledgement.status) {
                let readback = try exchange(.state)
                try requireOK(readback)
                guard let verified = readback.state, verified.session == session,
                      verified.sessionActive else { throw CommandError.readbackMismatch }
                state = verified
                deliveredContext = nil
                return
            }
            try requireOK(acknowledgement, allowDeferred: true)
            guard let acknowledgedState = acknowledgement.state,
                  acknowledgedState.session == session, acknowledgedState.sessionActive,
                  acknowledgedState.epoch == snapshot.epoch,
                  acknowledgedState.mode == .auto else { throw CommandError.readbackMismatch }
            let readback = try exchange(.state)
            try requireOK(readback)
            guard let verified = readback.state, verified.session == session,
                  verified.sessionActive else { throw CommandError.readbackMismatch }
            state = verified
            if verified.epoch != snapshot.epoch || verified.mode != .auto || verified.picker {
                deliveredContext = nil
                return
            }
            let deferred = acknowledgement.status == .deferred && verified.deferred
            guard deferred || (verified.selectedLayer == desiredLayer && !verified.deferred) else {
                throw CommandError.readbackMismatch
            }
            deliveredContext = ContextReceipt(epoch: snapshot.epoch, layer: desiredLayer)
            lastAcknowledgedLayer = desiredLayer
        } catch { try fail(error) }
    }

    public func pause(_ reason: PauseReason = .user) {
        releaseSession()
        phase = .paused(reason)
    }

    public func stop() {
        releaseSession()
        phase = .stopped
    }

    public var statusDescription: String {
        let mode = state.map { String(describing: $0.mode) } ?? "unknown"
        let layer = state.map { String($0.selectedLayer) } ?? "unknown"
        return "phase=\(phase) mode=\(mode) layer=\(layer) context=\(desiredLayer) session=\(session)"
    }

    private func releaseSession() {
        if phase == .ready { _ = try? exchange(.close) }
        transport.close()
        state = nil
        session = 0
        deliveredContext = nil
        lastAcknowledgedLayer = nil
    }

    private func fail(_ error: any Error) throws -> Never {
        transport.close()
        state = nil
        deliveredContext = nil
        lastAcknowledgedLayer = nil
        session = 0
        if case CommandError.status(.busyConfiguration) = error {
            phase = .paused(.configurationTraffic)
        } else {
            phase = .failed(String(describing: error))
        }
        throw error
    }

    private func requireOK(_ response: Response, allowDeferred: Bool = false) throws {
        guard response.status == .ok || (allowDeferred && response.status == .deferred) else {
            throw CommandError.status(response.status)
        }
    }

    private func exchange(_ opcode: Opcode, session suppliedSession: UInt32? = nil,
                          epoch: UInt32 = 0, sequence: UInt32 = 0, layer: UInt8 = 0) throws -> Response {
        guard !inFlight else { throw CommandError.transport("a command-mode request is already in flight") }
        inFlight = true
        defer { inFlight = false }
        guard requestID < UInt32.max else { throw CommandError.counterExhausted }
        requestID += 1
        let request = Request(opcode: opcode, id: requestID, session: suppliedSession ?? session,
                              epoch: epoch, sequence: sequence, layer: layer)
        try transport.send(request.bytes)
        let deadline = Date().addingTimeInterval(timeout)
        for _ in 0..<64 {
            let remaining = deadline.timeIntervalSinceNow
            guard remaining > 0, let bytes = try transport.receive(timeout: remaining) else {
                throw CommandError.timeout
            }
            guard bytes.first == 0xD3, bytes.count >= 2, bytes[1] == 0xAC else { continue }
            if bytes.count >= 8,
               bytes[3] != opcode.rawValue || bytes.read32(at: 4) != request.id { continue }
            let response = try Response.decode(bytes)
            guard response.id == request.id, response.opcode == opcode else { continue }
            return response
        }
        throw CommandError.timeout
    }
}
