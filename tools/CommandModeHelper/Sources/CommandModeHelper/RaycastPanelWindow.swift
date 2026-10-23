import CoreGraphics
import Foundation

struct RaycastPanelWindow {
    let ownerPID: Int
    let isOnscreen: Bool
    let layer: Int
    let alpha: Double
    let bounds: CGRect

    init?(metadata: [String: Any]) {
        guard let ownerPID = metadata[kCGWindowOwnerPID as String] as? Int,
              let isOnscreen = metadata[kCGWindowIsOnscreen as String] as? Bool,
              let layer = metadata[kCGWindowLayer as String] as? Int,
              let alpha = metadata[kCGWindowAlpha as String] as? Double,
              let boundsDictionary = metadata[kCGWindowBounds as String] as? [String: Any],
              let bounds = CGRect(dictionaryRepresentation: boundsDictionary as CFDictionary) else { return nil }
        self.ownerPID = ownerPID
        self.isOnscreen = isOnscreen
        self.layer = layer
        self.alpha = alpha
        self.bounds = bounds
    }

    func isVisibleModalPanel(ownedBy raycastPIDs: Set<pid_t>) -> Bool {
        raycastPIDs.contains { Int($0) == ownerPID } && isOnscreen &&
            layer == Int(CGWindowLevelForKey(.modalPanelWindow)) && alpha.isFinite && alpha > 0 &&
            bounds.origin.x.isFinite && bounds.origin.y.isFinite &&
            bounds.size.width.isFinite && bounds.size.height.isFinite && bounds.size.width > 0 && bounds.size.height > 0
    }
}
