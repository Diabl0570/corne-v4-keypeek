import Foundation

@MainActor
public final class MockReportTransport: ReportTransport {
    public let descriptor: DeviceDescriptor
    public private(set) var outputReports: [[UInt8]] = []
    public private(set) var isOpen = false
    public private(set) var closeCount = 0
    public private(set) var openCount = 0
    public var connected = true
    public var configurationBusy = false
    public var keysHeld = false
    public var transformReply: (([UInt8]) -> [[UInt8]])?
    public var beforeRequest: ((Opcode) -> Void)?
    public private(set) var mode: FirmwareMode = .typing
    public private(set) var selectedLayer: UInt8 = 0
    public private(set) var epoch: UInt32 = 1
    public private(set) var session: UInt32 = 0
    public private(set) var sequence: UInt32 = 0
    public private(set) var revision: UInt32 = 0
    public private(set) var picker = false
    private var pendingLayer: UInt8?
    private var inputReports: [[UInt8]] = []
    private var leaseDeadline: TimeInterval = 0
    private let now: () -> TimeInterval

    public init(descriptor: DeviceDescriptor = .commandMode,
                now: @escaping () -> TimeInterval = { Date.timeIntervalSinceReferenceDate }) {
        self.descriptor = descriptor
        self.now = now
    }

    public func open() throws {
        guard connected else { throw CommandError.disconnected }
        isOpen = true
        openCount += 1
    }

    public func close() {
        isOpen = false
        inputReports.removeAll()
        closeCount += 1
    }

    public func keyboardSelect(mode: FirmwareMode, layer: UInt8, picker: Bool = false) {
        self.mode = mode
        self.selectedLayer = layer
        self.picker = picker
        epoch &+= 1
        revision &+= 1
        pendingLayer = nil
    }

    public func send(_ report: [UInt8]) throws {
        guard connected, isOpen else { throw CommandError.disconnected }
        outputReports.append(report)
        guard report.count == 32, report[0] == 0xD3, report[1] == 0x43,
              report[2] == 1, let opcode = Opcode(rawValue: report[3]),
              report.read32(at: 4) != 0, report[21..<32].allSatisfy({ $0 == 0 }) else { return }
        beforeRequest?(opcode)
        expireLease()
        let requestSession = report.read32(at: 8)
        var status: ResponseStatus = .ok
        if opcode != .capabilities && configurationBusy {
            disarm()
            status = .busyConfiguration
        } else {
            switch opcode {
            case .capabilities: break
            case .open:
                if requestSession == 0 { status = .badRequest }
                else if requestSession != session {
                    disarm()
                    session = requestSession
                    epoch &+= 1
                    sequence = 0
                }
                leaseDeadline = now() + 2
            case .state:
                if requestSession != session || session == 0 { status = .wrongSession }
                else {
                    leaseDeadline = now() + 2
                    if !keysHeld, let pendingLayer {
                        selectedLayer = pendingLayer
                        self.pendingLayer = nil
                        revision &+= 1
                    }
                }
            case .context:
                if requestSession != session || session == 0 { status = .wrongSession }
                else if report.read32(at: 12) != epoch { status = .staleEpoch }
                else if mode != .auto || picker { status = .disarmed }
                else if !(6...10).contains(report[20]) { status = .invalidLayer }
                else if report.read32(at: 16) <= sequence { status = .staleSequence }
                else {
                    sequence = report.read32(at: 16)
                    if keysHeld { pendingLayer = report[20]; status = .deferred }
                    else { selectedLayer = report[20]; pendingLayer = nil; revision &+= 1 }
                }
            case .close:
                if requestSession != session || session == 0 { status = .wrongSession }
                else { disarm() }
            }
        }
        let reply = response(to: report, opcode: opcode, status: status)
        inputReports.append(contentsOf: transformReply?(reply) ?? [reply])
    }

    public func receive(timeout: TimeInterval) throws -> [UInt8]? {
        guard connected, isOpen else { throw CommandError.disconnected }
        return inputReports.isEmpty ? nil : inputReports.removeFirst()
    }

    private func expireLease() {
        if session != 0, now() >= leaseDeadline { disarm() }
    }

    private func disarm() {
        mode = selectedLayer == 0 ? .typing : .manual
        session = 0
        pendingLayer = nil
        sequence = 0
        epoch &+= 1
        revision &+= 1
    }

    private func response(to request: [UInt8], opcode: Opcode, status: ResponseStatus) -> [UInt8] {
        var bytes = [UInt8](repeating: 0, count: 32)
        bytes.replaceSubrange(0..<4, with: [0xD3, 0xAC, 1, opcode.rawValue])
        bytes.write(request.read32(at: 4), at: 4)
        bytes[8] = status.rawValue
        if opcode == .capabilities {
            bytes[9] = 16
            bytes[10] = 0x0F
            bytes[11] = 2
            bytes.replaceSubrange(12..<20, with: [0x89, 0x36, 0x2A, 0xC7, 0xFA, 0xD8, 0x89, 0x45])
            bytes.write(CommandRegistry.hash, at: 20)
            bytes.write(0x434D0001, at: 24)
        } else {
            bytes[9] = mode.rawValue
            bytes[10] = selectedLayer
            bytes[11] = (picker ? 1 : 0) | (pendingLayer != nil ? 4 : 0) | (session != 0 ? 8 : 0)
            bytes.write(session, at: 12)
            bytes.write(epoch, at: 16)
            bytes.write(revision, at: 20)
            let mask: UInt16 = 1 << (picker ? 15 : selectedLayer)
            bytes[24] = UInt8(truncatingIfNeeded: mask)
            bytes[25] = UInt8(truncatingIfNeeded: mask >> 8)
            bytes[26] = 16
            bytes[27] = 0x0F
            bytes.write(CommandRegistry.hash, at: 28)
        }
        return bytes
    }
}
