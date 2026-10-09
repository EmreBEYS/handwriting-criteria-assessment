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
    public let instructorRole: String

    enum CodingKeys: String, CodingKey {
        case id
        case courseID = "course_id"
        case semesterID = "semester_id"
        case academicYearID = "academic_year_id"
        case programID = "program_id"
        case sectionCode = "section_code"
        case instructorRole = "instructor_role"
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
