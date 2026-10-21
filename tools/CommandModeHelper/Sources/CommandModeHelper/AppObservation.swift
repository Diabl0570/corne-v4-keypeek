import AppKit
import CommandModeCore

@MainActor
struct AppObservation {
    let frontmost: String?
    let runningBundleIDs: Set<String>

    static func current() -> AppObservation {
        AppObservation(
            frontmost: NSWorkspace.shared.frontmostApplication?.bundleIdentifier,
            runningBundleIDs: Set(NSWorkspace.shared.runningApplications.compactMap(\.bundleIdentifier))
        )
    }

    func apply(to client: CommandClient) {
        client.observeApplications(frontmost: frontmost, runningBundleIDs: runningBundleIDs)
    }
}
