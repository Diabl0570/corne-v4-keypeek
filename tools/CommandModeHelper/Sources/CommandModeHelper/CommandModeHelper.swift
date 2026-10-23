import CommandModeCore
import Darwin
import Foundation

@main
@MainActor
struct CommandModeHelper {
    static func main() {
        do { try run(arguments: Array(CommandLine.arguments.dropFirst())) }
        catch {
            fputs("command-mode-helper: \(error)\n", stderr)
            exit(1)
        }
    }

    private static func run(arguments: [String]) throws {
        guard let command = arguments.first, command != "--help", command != "help" else {
            print(help)
            return
        }
        if command == "capability" {
            throw CommandError.transport("unsupported action; helper only reports app context; no voice, typing, or shortcut hooks")
        }
        guard ["run", "status", "dry-run"].contains(command) else {
            throw CommandError.transport("unknown command; use --help")
        }
        let options = Array(arguments.dropFirst())
        let allowed = command == "dry-run" ? ["--observe-apps", "--seconds", "--simulate-auto", "--simulate-timeout", "--simulate-missing"] : []
        var seconds: TimeInterval? = command == "dry-run" ? 8 : nil
        var index = 0
        while index < options.count {
            let option = options[index]
            guard allowed.contains(option) else { throw CommandError.transport("unknown option \(option)") }
            if option == "--seconds" {
                index += 1
                guard index < options.count, let value = Double(options[index]), value > 0, value <= 3600 else {
                    throw CommandError.transport("--seconds requires a number in 0...3600")
                }
                seconds = value
            }
            index += 1
        }
        if command == "dry-run" {
            let mock = MockReportTransport()
            let availableAt = Date().addingTimeInterval(1)
            if options.contains("--simulate-missing") {
                mock.connected = false
                print("mock fault: keyboard unavailable for one second")
            }
            let client = options.contains("--simulate-missing") ? nil : CommandClient(transport: mock)
            try client?.start()
            if client != nil, options.contains("--simulate-auto") { mock.keyboardSelect(mode: .auto, layer: 6) }
            if options.contains("--simulate-timeout") {
                var dropped = false
                mock.transformReply = { reply in
                    if !dropped, reply[3] == Opcode.state.rawValue {
                        dropped = true
                        print("mock fault: dropped one acknowledgement")
                        return []
                    }
                    return [reply]
                }
            }
            let runtime = HelperRuntime(
                client: client, observeApps: options.contains("--observe-apps"),
                makeClient: {
                    if options.contains("--simulate-missing") { mock.connected = Date() >= availableAt }
                    return CommandClient(transport: mock)
                }
            )
            runtime.run(seconds: seconds)
            print("mock output reports=\(mock.outputReports.count); native HID objects=0")
            return
        }
        if command == "status" {
            let transport = try NativeHIDTransport.discover()
            let client = CommandClient(transport: transport)
            print("descriptor supported=\(transport.descriptor.supported) product=\(transport.descriptor.product)")
            try client.checkCapabilities()
            print("capabilities verified; no session opened; registry=\(String(CommandRegistry.hash, radix: 16))")
            return
        }
        HelperRuntime(observeApps: true, makeClient: {
            CommandClient(transport: try NativeHIDTransport.discover())
        }).run(seconds: nil)
    }

    private static let help = """
    command-mode-helper run
    command-mode-helper status
    command-mode-helper dry-run [--observe-apps] [--seconds 8] [--simulate-auto] [--simulate-timeout | --simulate-missing]
    command-mode-helper capability <action>

    run stays in the foreground. Commands on stdin are status, pause, disable, resume, quit.
    Ctrl-C quits and closes the session. Pause stays paused until resume.
    Temporary HID failures reconnect with bounded backoff. A new session always starts disarmed.
    status checks descriptors and capabilities without opening a firmware session.
    dry-run creates only a mock transport. --observe-apps reads bundle IDs through NSWorkspace.
    Auto Command must be selected on the keyboard after every start, resume, or reconnect.
    No voice, shortcut, typing, Accessibility, EEPROM, or startup-installation actions exist.
    """
}

enum RuntimeRecovery: Equatable {
    case starting
    case active
    case waiting(deadline: TimeInterval, reason: CommandError)
    case userPaused
    case vialRunning
    case blocked(CommandError)
}

@MainActor
final class HelperRuntime {
    private(set) var client: CommandClient?
    private(set) var recovery: RuntimeRecovery
    private(set) var failures = 0
    private let observeApps: Bool
    private let makeClient: () throws -> CommandClient
    private let now: () -> TimeInterval
    private var running = true
    private var lastBundleID: String?
    private var lastStatus: String?
    private var input = ""
    private var pendingCommands: [String] = []

    init(client: CommandClient? = nil, observeApps: Bool,
         now: @escaping () -> TimeInterval = { ProcessInfo.processInfo.systemUptime },
         makeClient: @escaping () throws -> CommandClient) {
        self.client = client
        self.recovery = client?.phase == .ready ? .active : .starting
        self.observeApps = observeApps
        self.makeClient = makeClient
        self.now = now
    }

    var statusDescription: String {
        switch recovery {
        case .starting: "phase=connecting"
        case .active: client?.statusDescription ?? "phase=connecting"
        case .waiting(_, let error): "phase=retrying attempt=\(failures) error=\(error)"
        case .userPaused: "phase=paused(user)"
        case .vialRunning: "phase=paused(vialRunning)"
        case .blocked(let error): "phase=blocked error=\(error); correct the problem, then resume"
        }
    }

    func pause() {
        client?.pause()
        recovery = .userPaused
    }

    func resume() throws {
        failures = 0
        recovery = .starting
        do { try connect(observation: observation()) }
        catch { recover(error, now: now()); throw error }
    }

    private func observation() -> AppObservation {
        observeApps ? .current() : AppObservation(frontmost: nil, runningBundleIDs: [])
    }

    private func connect(observation: AppObservation) throws {
        client?.stop()
        client = nil
        if observation.runningBundleIDs.contains(CommandRegistry.configuratorBundleID) {
            recovery = .vialRunning
            return
        }
        let next = try makeClient()
        client = next
        observation.apply(to: next)
        try next.start()
        recovery = next.phase == .ready ? .active : .vialRunning
    }

    private func recover(_ error: any Error, now: TimeInterval) {
        let failure = error as? CommandError ?? .transport(String(describing: error))
        client?.stop()
        failures += 1
        switch failure.recovery {
        case .stop: recovery = .blocked(failure)
        case .reconnect, .configurationQuietPeriod:
            let delay = min(8, 0.5 * pow(2, Double(min(failures - 1, 4))))
            let minimum: TimeInterval = failure.recovery == .configurationQuietPeriod ? 2 : 0
            recovery = .waiting(deadline: now + max(minimum, delay), reason: failure)
        }
    }

    func tick(observation: AppObservation) {
        let timestamp = now()
        if case .userPaused = recovery { return }
        if case .blocked = recovery { return }
        if observation.runningBundleIDs.contains(CommandRegistry.configuratorBundleID) {
            if recovery != .vialRunning { client?.pause(.vialRunning) }
            recovery = .vialRunning
            return
        }
        if recovery == .vialRunning {
            recover(CommandError.status(.busyConfiguration), now: timestamp)
            return
        }
        do {
            switch recovery {
            case .waiting(let deadline, _) where timestamp < deadline: return
            case .waiting, .starting: try connect(observation: observation)
            default: break
            }
            guard recovery == .active, let client else { return }
            observation.apply(to: client)
            try client.poll()
            if client.phase == .ready { failures = 0 }
        } catch { recover(error, now: now()) }
    }

    func run(seconds: TimeInterval?) {
        let activation = observeApps ? AppActivationSignal() : nil
        signal(SIGINT, SIG_IGN)
        signal(SIGTERM, SIG_IGN)
        let signals = [SIGINT, SIGTERM].map { number in
            let source = DispatchSource.makeSignalSource(signal: number, queue: .main)
            source.setEventHandler { MainActor.assumeIsolated { self.running = false } }
            source.resume()
            return source
        }
        let stdinSource = DispatchSource.makeReadSource(fileDescriptor: STDIN_FILENO, queue: .main)
        stdinSource.setEventHandler {
            MainActor.assumeIsolated {
                let data = FileHandle.standardInput.availableData
                if data.isEmpty { stdinSource.cancel(); return }
                self.input += String(decoding: data, as: UTF8.self)
                while let newline = self.input.firstIndex(of: "\n") {
                    let command = String(self.input[..<newline]).trimmingCharacters(in: .whitespaces)
                    self.input.removeSubrange(...newline)
                    self.pendingCommands.append(command)
                }
            }
        }
        stdinSource.resume()
        let deadline = seconds.map { Date().addingTimeInterval($0) }
        defer {
            activation?.stop()
            stdinSource.cancel()
            signals.forEach { $0.cancel() }
            client?.stop()
            print(client?.statusDescription ?? "phase=stopped")
        }
        while running, deadline.map({ Date() < $0 }) ?? true {
            activation?.clear()
            let nextTick = Date().addingTimeInterval(0.25)
            let commands = pendingCommands
            pendingCommands.removeAll()
            commands.forEach(handle)
            guard running else { break }
            let current = observation()
            tick(observation: current)
            if observeApps, current.frontmost != lastBundleID {
                print("foreground bundle=\(current.frontmost ?? "unknown") context=\(client?.desiredLayer ?? 6)")
                lastBundleID = current.frontmost
            }
            if statusDescription != lastStatus {
                print(statusDescription)
                lastStatus = statusDescription
            }
            while running, activation?.pending != true, Date() < nextTick {
                _ = RunLoop.main.run(mode: .default, before: nextTick)
            }
        }
    }

    private func handle(_ command: String) {
        switch command {
        case "status": print(statusDescription)
        case "pause", "disable": pause()
        case "resume":
            do { try resume() }
            catch { print(statusDescription) }
        case "quit", "q": running = false
        default: print("commands: status, pause, disable, resume, quit")
        }
    }
}
