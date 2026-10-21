import CommandModeCore
import Foundation
import IOKit.hid

@MainActor
final class NativeHIDTransport: ReportTransport {
    let descriptor: DeviceDescriptor
    private let device: IOHIDDevice
    private let manager: IOHIDManager
    private let reportBuffer = ReportBuffer()
    private var reports: [[UInt8]] = []
    private var opened = false
    private var disconnected = false
    private var pendingOutput: PendingOutput?
    private var callbackRegistration: HIDCallbackRegistration?

    private init(device: IOHIDDevice, manager: IOHIDManager, descriptor: DeviceDescriptor) {
        self.device = device
        self.manager = manager
        self.descriptor = descriptor
    }

    static func discover() throws -> NativeHIDTransport {
        let manager = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(kIOHIDOptionsTypeNone))
        let match: [String: Any] = [
            kIOHIDVendorIDKey: 0x4653,
            kIOHIDProductIDKey: 0x0004,
            kIOHIDDeviceUsagePageKey: 0xFF60,
            kIOHIDDeviceUsageKey: 0x61,
        ]
        IOHIDManagerSetDeviceMatching(manager, match as CFDictionary)
        guard let devices = IOHIDManagerCopyDevices(manager) as? Set<IOHIDDevice>, !devices.isEmpty else {
            throw CommandError.transport("no Corne Raw HID interface found")
        }
        guard devices.count == 1, let device = devices.first else {
            throw CommandError.transport("multiple Corne Raw HID interfaces; connect one keyboard")
        }
        func number(_ key: String) -> Int { (IOHIDDeviceGetProperty(device, key as CFString) as? NSNumber)?.intValue ?? 0 }
        let descriptor = DeviceDescriptor(
            vendorID: number(kIOHIDVendorIDKey), productID: number(kIOHIDProductIDKey),
            usagePage: number(kIOHIDPrimaryUsagePageKey), usage: number(kIOHIDPrimaryUsageKey),
            product: IOHIDDeviceGetProperty(device, kIOHIDProductKey as CFString) as? String ?? "",
            release: number(kIOHIDVersionNumberKey)
        )
        return NativeHIDTransport(device: device, manager: manager, descriptor: descriptor)
    }

    func open() throws {
        guard descriptor.supported else { throw CommandError.unsupportedDevice }
        guard !opened else { return }
        guard IOHIDDeviceOpen(device, IOOptionBits(kIOHIDOptionsTypeNone)) == kIOReturnSuccess else {
            throw CommandError.transport("non-seizing IOHIDDeviceOpen failed")
        }
        opened = true
        disconnected = false
        let context = Unmanaged.passUnretained(self).toOpaque()
        let device = self.device
        let reportBuffer = self.reportBuffer
        callbackRegistration = HIDCallbackRegistration(
            context: context,
            registerInput: { context in
                IOHIDDeviceRegisterInputReportCallback(device, reportBuffer.bytes, 32, { context, result, _, _, _, report, length in
                    guard let context else { return }
                    MainActor.assumeIsolated {
                        let transport = Unmanaged<NativeHIDTransport>.fromOpaque(context).takeUnretainedValue()
                        guard result == kIOReturnSuccess, length == 32 else { return }
                        let bytes = Array(UnsafeBufferPointer(start: report, count: length))
                        guard bytes[0] == 0xD3, bytes[1] == 0xAC else { return }
                        if transport.reports.count < 64 { transport.reports.append(bytes) }
                    }
                }, context)
            },
            registerRemoval: { context in
                IOHIDDeviceRegisterRemovalCallback(device, { context, _, _ in
                    guard let context else { return }
                    MainActor.assumeIsolated {
                        Unmanaged<NativeHIDTransport>.fromOpaque(context).takeUnretainedValue().disconnected = true
                    }
                }, context)
            },
            unregisterInput: { context in
                IOHIDDeviceRegisterInputReportCallback(device, reportBuffer.bytes, 32, nil, context)
            },
            unregisterRemoval: { context in
                IOHIDDeviceRegisterRemovalCallback(device, nil, context)
            }
        )
        callbackRegistration?.install()
        IOHIDDeviceScheduleWithRunLoop(device, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)
    }

    func close() {
        guard opened else { return }
        callbackRegistration?.remove()
        IOHIDDeviceUnscheduleFromRunLoop(device, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)
        IOHIDDeviceClose(device, IOOptionBits(kIOHIDOptionsTypeNone))
        callbackRegistration = nil
        opened = false
        reports.removeAll()
        pendingOutput = nil
    }

    func send(_ report: [UInt8]) throws {
        guard opened, !disconnected else { throw CommandError.disconnected }
        guard descriptor.supported, report.count == 32,
              report[0] == 0xD3, report[1] == 0x43 else {
            throw CommandError.transport("refused non-command-mode output")
        }
        guard pendingOutput?.result != nil || pendingOutput == nil else {
            throw CommandError.transport("an IOHID output is already in flight")
        }
        let output = PendingOutput(report)
        let context = Unmanaged.passRetained(output).toOpaque()
        pendingOutput = output
        let result = IOHIDDeviceSetReportWithCallback(
            device, kIOHIDReportTypeOutput, 0, output.bytes, 32, 400,
            { context, result, _, _, _, _, _ in
                guard let context else { return }
                let output = Unmanaged<PendingOutput>.fromOpaque(context).takeRetainedValue()
                output.complete(result)
            }, context
        )
        if result != kIOReturnSuccess { Unmanaged<PendingOutput>.fromOpaque(context).release() }
        guard result == kIOReturnSuccess else { throw CommandError.transport("IOHID output failed \(result)") }
    }

    func receive(timeout: TimeInterval) throws -> [UInt8]? {
        let deadline = Date().addingTimeInterval(timeout)
        while true {
            guard opened, !disconnected else { throw CommandError.disconnected }
            if let result = pendingOutput?.result, result != kIOReturnSuccess {
                throw CommandError.transport("IOHID output completion failed \(result)")
            }
            if !reports.isEmpty, pendingOutput?.result != nil { return reports.removeFirst() }
            guard deadline.timeIntervalSinceNow > 0 else { return nil }
            _ = RunLoop.main.run(mode: .default, before: min(deadline, Date().addingTimeInterval(0.01)))
        }
    }

}

private final class ReportBuffer: @unchecked Sendable {
    let bytes = UnsafeMutablePointer<UInt8>.allocate(capacity: 32)
    deinit { bytes.deallocate() }
}

private final class PendingOutput: @unchecked Sendable {
    let bytes = UnsafeMutablePointer<UInt8>.allocate(capacity: 32)
    private let lock = NSLock()
    private var completion: IOReturn?

    init(_ report: [UInt8]) {
        bytes.initialize(from: report, count: 32)
    }

    var result: IOReturn? {
        lock.lock()
        defer { lock.unlock() }
        return completion
    }

    func complete(_ result: IOReturn) {
        lock.lock()
        completion = result
        lock.unlock()
    }

    deinit { bytes.deallocate() }
}
