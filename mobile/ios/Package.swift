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
        .target(name: "AppCore"),
        .executableTarget(
            name: "HandwritingCriteriaAssessmentApp",
            dependencies: ["AppCore"]
        ),
        .testTarget(name: "AppCoreTests", dependencies: ["AppCore"]),
    ]
)
