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
            if options.contains("--simulate-missing") { mock.connected = false }
            let client = CommandClient(transport: mock)
            try client.start()
            if options.contains("--simulate-auto") { mock.keyboardSelect(mode: .auto, layer: 6) }
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
        let transport = try NativeHIDTransport.discover()
        let client = CommandClient(transport: transport)
        if command == "status" {
            print("descriptor supported=\(transport.descriptor.supported) product=\(transport.descriptor.product)")
            try client.checkCapabilities()
            print("capabilities verified; no session opened; registry=\(String(CommandRegistry.hash, radix: 16))")
            return
        }
        AppObservation.current().apply(to: client)
        try client.start()
        HelperRuntime(client: client, observeApps: true, makeClient: {
            CommandClient(transport: try NativeHIDTransport.discover())
        }).run(seconds: nil)
    }

    private static let help = """
    command-mode-helper run
    command-mode-helper status
    command-mode-helper dry-run [--observe-apps] [--seconds 8] [--simulate-auto]
    command-mode-helper capability <action>

    run stays in the foreground. Commands on stdin are status, pause, disable, resume, quit.
    Ctrl-C quits and closes the session. Resume opens a fresh disarmed session.
    status checks descriptors and capabilities without opening a firmware session.
    dry-run creates only a mock transport. --observe-apps reads bundle IDs through NSWorkspace.
    Auto Command must be selected on the keyboard after every start, resume, or reconnect.
    No voice, shortcut, typing, Accessibility, EEPROM, or startup-installation actions exist.
    """
}

@MainActor
final class HelperRuntime {
    private(set) var client: CommandClient
    private let observeApps: Bool
    private let makeClient: () throws -> CommandClient
    private var running = true
    private var lastBundleID: String?
    private var lastStatus: String?
    private var input = ""
    private var pendingCommands: [String] = []

    init(client: CommandClient, observeApps: Bool, makeClient: @escaping () throws -> CommandClient) {
        self.client = client
        self.observeApps = observeApps
        self.makeClient = makeClient
    }

    func resume() throws {
        let bundleID = client.observedBundleID
        client.stop()
        client = try makeClient()
        client.observe(bundleID: bundleID)
        if observeApps { AppObservation.current().apply(to: client) }
        try client.start()
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
            client.stop()
            print(client.statusDescription)
        }
        while running, deadline.map({ Date() < $0 }) ?? true {
            activation?.clear()
            let nextTick = Date().addingTimeInterval(0.25)
            let commands = pendingCommands
            pendingCommands.removeAll()
            commands.forEach(handle)
            guard running else { break }
            if observeApps {
                let observation = AppObservation.current()
                observation.apply(to: client)
                if observation.frontmost != lastBundleID {
                    print("foreground bundle=\(observation.frontmost ?? "unknown") context=\(client.desiredLayer)")
                    lastBundleID = observation.frontmost
                }
            }
            do { try client.poll() }
            catch { print("status error=\(error); explicit resume required") }
            if client.statusDescription != lastStatus {
                print(client.statusDescription)
                lastStatus = client.statusDescription
            }
            while running, activation?.pending != true, Date() < nextTick {
                _ = RunLoop.main.run(mode: .default, before: nextTick)
            }
        }
    }

    private func handle(_ command: String) {
        switch command {
        case "status": print(client.statusDescription)
        case "pause", "disable": client.pause()
        case "resume":
            do { try resume() }
            catch { print("resume error=\(error)") }
        case "quit", "q": running = false
        default: print("commands: status, pause, disable, resume, quit")
        }
    }
}
