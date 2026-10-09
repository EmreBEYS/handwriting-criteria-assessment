import Foundation
import Testing
@testable import AppCore

@Test func routesRemainDistinct() {
    let selection = ExamSelection(
        offeringID: UUID(),
        examID: UUID(),
        courseTitle: "CENG301",
        examTitle: "Midterm"
    )
    #expect(AppRoute.captureUpload(selection) != .analysis(scanID: UUID(), selection: selection))
}
