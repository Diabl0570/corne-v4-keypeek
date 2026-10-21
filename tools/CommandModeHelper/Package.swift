// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "CommandModeHelper",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "CommandModeCore", targets: ["CommandModeCore"]),
        .executable(name: "command-mode-helper", targets: ["CommandModeHelper"]),
    ],
    targets: [
        .target(name: "CommandModeCore"),
        .executableTarget(name: "CommandModeHelper", dependencies: ["CommandModeCore"]),
        .testTarget(name: "CommandModeCoreTests", dependencies: ["CommandModeCore"]),
        .testTarget(name: "CommandModeHelperTests", dependencies: ["CommandModeHelper", "CommandModeCore"]),
    ]
)
