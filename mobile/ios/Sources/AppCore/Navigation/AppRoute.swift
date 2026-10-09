import Foundation

public struct ExamSelection: Hashable, Sendable {
    public let offeringID: UUID
    public let examID: UUID
    public let courseTitle: String
    public let examTitle: String

    public init(offeringID: UUID, examID: UUID, courseTitle: String, examTitle: String) {
        self.offeringID = offeringID
        self.examID = examID
        self.courseTitle = courseTitle
        self.examTitle = examTitle
    }
}

public enum AppRoute: Hashable {
    case captureUpload(ExamSelection)
    case analysis(scanID: UUID, selection: ExamSelection)
    case results(ConfirmationResult)
}
