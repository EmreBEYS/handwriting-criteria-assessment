// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "HandwritingCriteriaAssessment",
    platforms: [
        .iOS(.v16),
        .macOS(.v14),
    ],
    products: [
        .executable(
            name: "HandwritingCriteriaAssessmentApp",
            targets: ["HandwritingCriteriaAssessmentApp"]
        ),
    ],
    dependencies: [
        .package(
            url: "https://github.com/microsoft/onnxruntime-swift-package-manager",
            exact: "1.24.2"
        ),
    ],
    targets: [
        .target(
            name: "AppCore",
            dependencies: [
                .product(name: "onnxruntime", package: "onnxruntime-swift-package-manager"),
            ],
            exclude: [
                "Features",
                "Navigation",
                "Networking",
                "ScanQueue",
                "Session",
            ],
            resources: [.copy("Resources/digit-crnn-v3.onnx")]
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
            ],
            resources: [.copy("RecognizerFixtures")]
        ),
    ]
)
