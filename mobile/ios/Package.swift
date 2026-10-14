// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "HandwritingCriteriaAssessment",
    platforms: [
        .iOS(.v16),
        .macOS(.v13),
    ],
    products: [
        .executable(
            name: "HandwritingCriteriaAssessmentApp",
            targets: ["HandwritingCriteriaAssessmentApp"]
        ),
    ],
    targets: [
        .target(
            name: "AppCore",
            exclude: [
                "Features",
                "Navigation",
                "Networking",
                "ScanQueue",
                "Session",
            ]
        ),
        .executableTarget(
            name: "HandwritingCriteriaAssessmentApp",
            dependencies: ["AppCore"],
            exclude: ["HandwritingCriteriaAssessmentApp 2.swift"]
        ),
        .testTarget(
            name: "AppCoreTests",
            dependencies: ["AppCore"],
            exclude: [
                "APIClientTests.swift",
                "AppRouteTests.swift",
                "AppRouteTests 2.swift",
                "PendingScanStoreTests.swift",
            ]
        ),
    ]
)
