import Foundation

public struct CommandDefinition: Equatable, Sendable {
    public let id: UInt8
    public let name: String
    public let bundleIDs: [String]
    public let automatic: Bool

    public init(id: UInt8, name: String, bundleIDs: [String], automatic: Bool) {
        self.id = id
        self.name = name
        self.bundleIDs = bundleIDs
        self.automatic = automatic
    }
}

public struct DeviceDescriptor: Equatable, Sendable {
    public let vendorID: Int
    public let productID: Int
    public let usagePage: Int
    public let usage: Int
    public let product: String
    public let release: Int

    public init(vendorID: Int, productID: Int, usagePage: Int, usage: Int, product: String, release: Int) {
        self.vendorID = vendorID
        self.productID = productID
        self.usagePage = usagePage
        self.usage = usage
        self.product = product
        self.release = release
    }

    public var supported: Bool {
        vendorID == 0x4653 && productID == 0x0004 && usagePage == 0xFF60 && usage == 0x61
            && product == "Corne v4 CM1" && release == 0x0411
    }

    public static let commandMode = DeviceDescriptor(
        vendorID: 0x4653, productID: 4, usagePage: 0xFF60, usage: 0x61,
        product: "Corne v4 CM1", release: 0x0411
    )
}

public enum CommandError: Error, Equatable, CustomStringConvertible {
    case unsupportedDevice
    case malformedResponse
    case incompatibleCapabilities
    case timeout
    case disconnected
    case deviceNotFound
    case multipleDevices
    case hidUnavailable(operation: String, code: Int32)
    case hidFailure(operation: String, code: Int32)
    case permissionDenied(Int32)
    case outputInFlight
    case transport(String)
    case status(ResponseStatus)
    case readbackMismatch
    case counterExhausted

    public var description: String {
        switch self {
        case .unsupportedDevice: "unsupported firmware descriptor; no output report sent"
        case .malformedResponse: "malformed command-mode response"
        case .incompatibleCapabilities: "firmware UID, schema, capabilities, or registry mismatch"
        case .timeout: "command-mode acknowledgement timed out"
        case .disconnected: "device disconnected"
        case .deviceNotFound: "no Corne Raw HID interface found; waiting for the keyboard"
        case .multipleDevices: "multiple Corne Raw HID interfaces; connect one keyboard"
        case .hidUnavailable(let operation, let code): "HID \(operation) temporarily unavailable (\(code))"
        case .hidFailure(let operation, let code): "HID \(operation) failed (\(code))"
        case .permissionDenied(let code): "HID access denied (\(code)); check macOS permissions, then resume"
        case .outputInFlight: "HID output is still pending after the acknowledgement deadline"
        case .transport(let message): message
        case .status(let status): "firmware returned \(status)"
        case .readbackMismatch: "firmware readback does not match acknowledgement"
        case .counterExhausted: "session counter exhausted; restart with a fresh session"
        }
    }
}

public enum FailureRecovery: Equatable {
    case reconnect
    case configurationQuietPeriod
    case stop
}

extension CommandError {
    public var recovery: FailureRecovery {
        switch self {
        case .timeout, .disconnected, .deviceNotFound, .hidUnavailable, .outputInFlight, .counterExhausted,
             .status(.wrongSession): .reconnect
        case .status(.busyConfiguration): .configurationQuietPeriod
        default: .stop
        }
    }
}

public enum Opcode: UInt8, Sendable {
    case capabilities = 1, open, state, context, close
}

public enum ResponseStatus: UInt8, Sendable {
    case ok, deferred, disarmed, staleEpoch, staleSequence, invalidLayer, badRequest,
         wrongSession, busyConfiguration, unsupportedVersion
}

public enum FirmwareMode: UInt8, Sendable {
    case typing, manual, auto
}

public struct FirmwareState: Equatable, Sendable {
    public let mode: FirmwareMode
    public let selectedLayer: UInt8
    public let flags: UInt8
    public let session: UInt32
    public let epoch: UInt32
    public let revision: UInt32
    public let appliedMask: UInt16

    public var picker: Bool { flags & 1 != 0 }
    public var mirror: Bool { flags & 2 != 0 }
    public var deferred: Bool { flags & 4 != 0 }
    public var sessionActive: Bool { flags & 8 != 0 }

    public init(mode: FirmwareMode, selectedLayer: UInt8, flags: UInt8, session: UInt32,
                epoch: UInt32, revision: UInt32, appliedMask: UInt16) {
        self.mode = mode
        self.selectedLayer = selectedLayer
        self.flags = flags
        self.session = session
        self.epoch = epoch
        self.revision = revision
        self.appliedMask = appliedMask
    }
}

public struct Request: Equatable, Sendable {
    public let opcode: Opcode
    public let id: UInt32
    public let session: UInt32
    public let epoch: UInt32
    public let sequence: UInt32
    public let layer: UInt8

    public init(opcode: Opcode, id: UInt32, session: UInt32 = 0, epoch: UInt32 = 0,
                sequence: UInt32 = 0, layer: UInt8 = 0) {
        self.opcode = opcode
        self.id = id
        self.session = session
        self.epoch = epoch
        self.sequence = sequence
        self.layer = layer
    }

    public var bytes: [UInt8] {
        var bytes = [UInt8](repeating: 0, count: 32)
        bytes.replaceSubrange(0..<4, with: [0xD3, 0x43, 1, opcode.rawValue])
        bytes.write(id, at: 4)
        bytes.write(session, at: 8)
        bytes.write(epoch, at: 12)
        bytes.write(sequence, at: 16)
        bytes[20] = layer
        return bytes
    }
}

public struct Response: Equatable, Sendable {
    public let opcode: Opcode
    public let id: UInt32
    public let status: ResponseStatus
    public let state: FirmwareState?

    public static func decode(_ bytes: [UInt8]) throws -> Response {
        guard bytes.count == 32, bytes[0] == 0xD3, bytes[1] == 0xAC, bytes[2] == 1,
              let opcode = Opcode(rawValue: bytes[3]), bytes.read32(at: 4) != 0,
              let status = ResponseStatus(rawValue: bytes[8]) else {
            throw CommandError.malformedResponse
        }
        if opcode == .capabilities {
            guard bytes[9] == 16, bytes[10] == 0x0F, bytes[11] == 2,
                  Array(bytes[12..<20]) == [0x89, 0x36, 0x2A, 0xC7, 0xFA, 0xD8, 0x89, 0x45],
                  bytes.read32(at: 20) == CommandRegistry.hash,
                  bytes.read32(at: 24) == 0x434D0001,
                  bytes[28..<32].allSatisfy({ $0 == 0 }) else {
                throw CommandError.incompatibleCapabilities
            }
            return Response(opcode: opcode, id: bytes.read32(at: 4), status: status, state: nil)
        }
        guard let mode = FirmwareMode(rawValue: bytes[9]), bytes[10] < 16,
              bytes[11] & 0xF0 == 0, bytes[26] == 16, bytes[27] == 0x0F,
              bytes.read32(at: 28) == CommandRegistry.hash else {
            throw CommandError.malformedResponse
        }
        let state = FirmwareState(mode: mode, selectedLayer: bytes[10], flags: bytes[11],
                                  session: bytes.read32(at: 12), epoch: bytes.read32(at: 16),
                                  revision: bytes.read32(at: 20), appliedMask: bytes.read16(at: 24))
        guard !state.sessionActive || state.session != 0 else { throw CommandError.malformedResponse }
        return Response(opcode: opcode, id: bytes.read32(at: 4), status: status, state: state)
    }
}

extension Array where Element == UInt8 {
    func read32(at index: Int) -> UInt32 {
        (0..<4).reduce(UInt32(0)) { $0 | UInt32(self[index + $1]) << (8 * $1) }
    }

    func read16(at index: Int) -> UInt16 {
        UInt16(self[index]) | UInt16(self[index + 1]) << 8
    }

    mutating func write(_ value: UInt32, at index: Int) {
        for offset in 0..<4 { self[index + offset] = UInt8(truncatingIfNeeded: value >> (offset * 8)) }
    }
}
