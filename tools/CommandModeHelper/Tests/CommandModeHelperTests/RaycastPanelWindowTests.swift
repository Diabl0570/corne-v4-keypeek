import CoreGraphics
import Foundation
import Testing
@testable import CommandModeHelper

@Suite
struct RaycastPanelWindowTests {
    private var metadata: [String: Any] {
        [kCGWindowOwnerPID as String: 35600,
         kCGWindowIsOnscreen as String: true,
         kCGWindowLayer as String: 8,
         kCGWindowAlpha as String: 1.0,
         kCGWindowBounds as String: ["X": 1068.0, "Y": 429.0, "Width": 750.0, "Height": 475.0]]
    }

    @Test func recordedVisiblePanelMatchesCurrentRaycastPID() throws {
        let window = try #require(RaycastPanelWindow(metadata: metadata))
        #expect(CGWindowLevelForKey(.modalPanelWindow) == 8)
        #expect(window.isVisibleModalPanel(ownedBy: [35600]))
        #expect(!window.isVisibleModalPanel(ownedBy: []))
        #expect(!window.isVisibleModalPanel(ownedBy: [35601]))
    }

    @Test func settingsAndOtherNonPanelWindowsAreExcluded() throws {
        for layer in [0, 3, 24, 101] {
            var data = metadata
            data[kCGWindowLayer as String] = layer
            let window = try #require(RaycastPanelWindow(metadata: data))
            #expect(!window.isVisibleModalPanel(ownedBy: [35600]))
        }
    }

    @Test func hiddenTransparentAndInvalidWindowsAreExcluded() throws {
        var hidden = metadata
        hidden[kCGWindowIsOnscreen as String] = false
        #expect(try #require(RaycastPanelWindow(metadata: hidden)).isVisibleModalPanel(ownedBy: [35600]) == false)
        for alpha in [0.0, -1.0, Double.nan, .infinity] {
            var data = metadata
            data[kCGWindowAlpha as String] = alpha
            let window = try #require(RaycastPanelWindow(metadata: data))
            #expect(!window.isVisibleModalPanel(ownedBy: [35600]))
        }
        for (field, value) in [("X", Double.nan), ("Y", .infinity), ("Width", 0.0),
                               ("Width", -1.0), ("Height", 0.0), ("Height", .infinity)] {
            var data = metadata
            var bounds = try #require(data[kCGWindowBounds as String] as? [String: Double])
            bounds[field] = value
            data[kCGWindowBounds as String] = bounds
            let visible = RaycastPanelWindow(metadata: data)?.isVisibleModalPanel(ownedBy: [35600]) ?? false
            #expect(!visible)
        }
    }

    @Test func missingMetadataIsRejectedWithoutTitlesOrWindowContents() {
        for key in metadata.keys {
            var data = metadata
            data.removeValue(forKey: key)
            #expect(RaycastPanelWindow(metadata: data) == nil)
        }
        var data = metadata
        data[kCGWindowBounds as String] = ["Width": 750.0]
        #expect(RaycastPanelWindow(metadata: data) == nil)
    }
}
