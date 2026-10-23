import AppKit
import Foundation

@MainActor
final class AppActivationSignal {
    private(set) var pending = false
    private let center: NotificationCenter
    private var observer: (any NSObjectProtocol)?

    init(center: NotificationCenter = NSWorkspace.shared.notificationCenter) {
        self.center = center
        observer = center.addObserver(forName: NSWorkspace.didActivateApplicationNotification,
                                      object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { self?.pending = true }
        }
    }

    func clear() { pending = false }

    func stop() {
        if let observer { center.removeObserver(observer) }
        observer = nil
        pending = false
    }
}
