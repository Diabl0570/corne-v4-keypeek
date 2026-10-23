import AppKit
import CommandModeCore
import CoreGraphics

@MainActor
struct AppObservation {
    private static let raycastBundleID = "com.raycast.macos"
    let frontmost: String?
    let runningBundleIDs: Set<String>
    let raycastPanelVisible: Bool

    init(frontmost: String?, runningBundleIDs: Set<String>, raycastPanelVisible: Bool = false) {
        self.frontmost = frontmost
        self.runningBundleIDs = runningBundleIDs
        self.raycastPanelVisible = raycastPanelVisible
    }

    static func current() -> AppObservation {
        let applications = NSWorkspace.shared.runningApplications
        let raycastPIDs = Set(applications.filter { $0.bundleIdentifier == raycastBundleID }.map(\.processIdentifier))
        let windows = raycastPIDs.isEmpty ? [] :
            CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
        return AppObservation(
            frontmost: NSWorkspace.shared.frontmostApplication?.bundleIdentifier,
            runningBundleIDs: Set(applications.compactMap(\.bundleIdentifier)),
            raycastPanelVisible: windows.compactMap(RaycastPanelWindow.init).contains {
                $0.isVisibleModalPanel(ownedBy: raycastPIDs)
            }
        )
    }

    func apply(to client: CommandClient) {
        let raycastIsFrontmost = frontmost == Self.raycastBundleID
        client.observeApplications(frontmost: raycastIsFrontmost ? nil : frontmost,
                                   runningBundleIDs: runningBundleIDs,
                                   typingOverride: raycastPanelVisible || raycastIsFrontmost)
    }

    var diagnosticDescription: String {
        "foreground bundle=\(frontmost ?? "unknown") raycastPanel=\(raycastPanelVisible)"
    }
}
