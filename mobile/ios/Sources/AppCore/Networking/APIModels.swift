import Foundation

public struct APIErrorEnvelope: Decodable, Sendable {
    public let error: APIErrorDetail
}

public struct APIErrorDetail: Decodable, Sendable {
    public let code: String
    public let message: String
    public let requestID: String

    enum CodingKeys: String, CodingKey {
        case code, message
        case requestID = "request_id"
    }
}

public enum APIClientError: Error, LocalizedError, Equatable, Sendable {
    case invalidResponse
    case server(statusCode: Int, code: String, message: String)
    case transport(String)
    case noSession

    public var errorDescription: String? {
        switch self {
        case .invalidResponse:
            "Sunucudan geçersiz bir yanıt alındı."
        case let .server(_, _, message):
            message
        case let .transport(message):
            message
        case .noSession:
            "Oturum bulunamadı. Lütfen yeniden giriş yapın."
        }
    }
}

public struct UserProfile: Codable, Hashable, Sendable {
    public let id: UUID
    public let institutionID: UUID
    public let email: String
    public let firstName: String
    public let lastName: String
    public let role: String

    public var displayName: String { "\(firstName) \(lastName)" }

    enum CodingKeys: String, CodingKey {
        case id, email, role
        case institutionID = "institution_id"
        case firstName = "first_name"
        case lastName = "last_name"
    }
}

public struct TokenPair: Codable, Equatable, Sendable {
    public let accessToken: String
    public let refreshToken: String
    public let expiresIn: Int

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
    }
}

public struct AuthData: Decodable, Sendable {
    public let user: UserProfile
    public let tokens: TokenPair
}

public struct AuthEnvelope: Decodable, Sendable {
    public let data: AuthData
}

public struct DataEnvelope<Value: Decodable & Sendable>: Decodable, Sendable {
    public let data: Value
}

public struct CourseOffering: Codable, Hashable, Identifiable, Sendable {
    public let id: UUID
    public let courseID: UUID
    public let semesterID: UUID
    public let academicYearID: UUID
    public let programID: UUID
    public let sectionCode: String
    public let courseCode: String
    public let courseName: String
    public let academicYearLabel: String
    public let season: String
    public let instructorRole: String

    public var displayName: String {
        "\(courseCode) — \(courseName) (\(academicYearLabel) / \(season == "fall" ? "Güz" : "Bahar"))"
    }

    enum CodingKeys: String, CodingKey {
        case id
        case courseID = "course_id"
        case semesterID = "semester_id"
        case academicYearID = "academic_year_id"
        case programID = "program_id"
        case sectionCode = "section_code"
        case courseCode = "course_code"
        case courseName = "course_name"
        case academicYearLabel = "academic_year_label"
        case season
        case instructorRole = "instructor_role"
    }
}

public struct RosterStudent: Codable, Hashable, Identifiable, Sendable {
    public let id: UUID
    public let studentNumber: String
    public let firstName: String
    public let lastName: String

    public var displayName: String { "\(studentNumber) — \(firstName) \(lastName)" }

    enum CodingKeys: String, CodingKey {
        case id
        case studentNumber = "student_number"
        case firstName = "first_name"
        case lastName = "last_name"
    }
}

public struct Enrollment: Codable, Hashable, Sendable {
    public let student: RosterStudent
    public let isActive: Bool

    enum CodingKeys: String, CodingKey {
        case student
        case isActive = "is_active"
    }
}

public struct PaperAnswerPrediction: Codable, Hashable, Identifiable, Sendable {
    public var id: UUID { questionID }
    public let questionID: UUID
    public let questionNumber: Int
    public let maximumScore: String
    public let predictedScore: String?
    public let confidence: String?
    public let requiresReview: Bool

    enum CodingKeys: String, CodingKey {
        case questionID = "question_id"
        case questionNumber = "question_number"
        case maximumScore = "maximum_score"
        case predictedScore = "predicted_score"
        case confidence
        case requiresReview = "requires_review"
    }
}

public struct ExamPaperPrediction: Codable, Hashable, Sendable {
    public let id: UUID
    public let matchedStudentID: UUID?
    public let resolvedStudentName: String?
    public let predictedStudentNumber: String?
    public let studentNumberConfidence: String?
    public let reviewReasons: [String]
    public let status: String
    public let predictedTotalScore: String?
    public let maximumTotalScore: String
    public let answers: [PaperAnswerPrediction]

    enum CodingKeys: String, CodingKey {
        case id, status, answers
        case matchedStudentID = "matched_student_id"
        case resolvedStudentName = "resolved_student_name"
        case predictedStudentNumber = "predicted_student_number"
        case studentNumberConfidence = "student_number_confidence"
        case reviewReasons = "review_reasons"
        case predictedTotalScore = "predicted_total_score"
        case maximumTotalScore = "maximum_total_score"
    }
}

public struct ScanJob: Codable, Hashable, Identifiable, Sendable {
    public let id: UUID
    public let examID: UUID
    public let status: String
    public let modelVersion: String?
    public let errorCode: String?
    public let errorMessage: String?
    public let savedAt: String?
    public let paper: ExamPaperPrediction?

    public var isPending: Bool { status == "queued" || status == "processing" }

    enum CodingKeys: String, CodingKey {
        case id, status, paper
        case examID = "exam_id"
        case modelVersion = "model_version"
        case errorCode = "error_code"
        case errorMessage = "error_message"
        case savedAt = "saved_at"
    }
}

public struct FinalAnswerInput: Encodable, Equatable, Sendable {
    public let questionID: UUID
    public let finalScore: String

    enum CodingKeys: String, CodingKey {
        case questionID = "question_id"
        case finalScore = "final_score"
    }
}

public struct ConfirmationInput: Encodable, Equatable, Sendable {
    public let studentID: UUID
    public let answers: [FinalAnswerInput]
    public let correctionReason: String?

    enum CodingKeys: String, CodingKey {
        case studentID = "student_id"
        case answers
        case correctionReason = "correction_reason"
    }
}

public struct ConfirmationResult: Codable, Hashable, Sendable {
    public let paperID: UUID
    public let scanID: UUID
    public let status: String
    public let studentID: UUID
    public let totalScore: String
    public let maximumTotalScore: String
    public let savedAt: String

    enum CodingKeys: String, CodingKey {
        case status
        case paperID = "paper_id"
        case scanID = "scan_id"
        case studentID = "student_id"
        case totalScore = "total_score"
        case maximumTotalScore = "maximum_total_score"
        case savedAt = "saved_at"
    }
}

public struct QuestionAnalysis: Codable, Hashable, Identifiable, Sendable {
    public var id: UUID { questionID }
    public let questionID: UUID
    public let questionNumber: Int
    public let maximumScore: String
    public let averageScore: String
    public let successPercentage: String
    public let responseCount: Int

    enum CodingKeys: String, CodingKey {
        case questionID = "question_id"
        case questionNumber = "question_number"
        case maximumScore = "maximum_score"
        case averageScore = "average_score"
        case successPercentage = "success_percentage"
        case responseCount = "response_count"
    }
}

public struct ProgramOutcomeAnalysis: Codable, Hashable, Identifiable, Sendable {
    public var id: UUID { programOutcomeID }
    public let programOutcomeID: UUID
    public let code: String
    public let description: String
    public let achievedScore: String
    public let maximumScore: String
    public let successPercentage: String

    enum CodingKeys: String, CodingKey {
        case programOutcomeID = "program_outcome_id"
        case code, description
        case achievedScore = "achieved_score"
        case maximumScore = "maximum_score"
        case successPercentage = "success_percentage"
    }
}

public struct ExamAnalysis: Codable, Hashable, Sendable {
    public let examID: UUID
    public let confirmedPaperCount: Int
    public let questions: [QuestionAnalysis]
    public let programOutcomes: [ProgramOutcomeAnalysis]

    enum CodingKeys: String, CodingKey {
        case examID = "exam_id"
        case confirmedPaperCount = "confirmed_paper_count"
        case questions
        case programOutcomes = "program_outcomes"
    }
}

public struct ExamSummary: Codable, Hashable, Identifiable, Sendable {
    public let id: UUID
    public let courseOfferingID: UUID
    public let type: String
    public let title: String
    public let totalScore: String
    public let status: String

    public var isScannable: Bool { status == "active" }

    enum CodingKeys: String, CodingKey {
        case id, type, title, status
        case courseOfferingID = "course_offering_id"
        case totalScore = "total_score"
    }
}
