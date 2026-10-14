import Foundation
import CoreGraphics

public struct NormalizedRect: Codable, Hashable, Sendable {
    public let x: Double
    public let y: Double
    public let width: Double
    public let height: Double

    public init(x: Double, y: Double, width: Double, height: Double) {
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    }

    public var visionRegion: CGRect {
        CGRect(x: x, y: 1 - y - height, width: width, height: height)
    }
}

public struct ExamQuestionTemplate: Identifiable, Codable, Hashable, Sendable {
    public let id: UUID
    public var number: Int
    public var maximumScore: Double
    public var programOutcome: String
    public var scoreRegion: NormalizedRect

    public init(
        id: UUID = UUID(),
        number: Int,
        maximumScore: Double,
        programOutcome: String,
        scoreRegion: NormalizedRect
    ) {
        self.id = id
        self.number = number
        self.maximumScore = maximumScore
        self.programOutcome = programOutcome
        self.scoreRegion = scoreRegion
    }
}

public struct ExamTemplate: Codable, Hashable, Sendable {
    public static let maximumQuestionCount = 12

    public var name: String
    public var courseTitle: String
    public var studentNameRegion: NormalizedRect
    public var totalScoreRegion: NormalizedRect
    public var questions: [ExamQuestionTemplate]

    public init(
        name: String,
        courseTitle: String,
        studentNameRegion: NormalizedRect,
        totalScoreRegion: NormalizedRect,
        questions: [ExamQuestionTemplate]
    ) {
        self.name = name
        self.courseTitle = courseTitle
        self.studentNameRegion = studentNameRegion
        self.totalScoreRegion = totalScoreRegion
        self.questions = questions
    }

    public static func inonuFixedV1(questionCount: Int = 5) -> ExamTemplate {
        let count = min(max(questionCount, 1), maximumQuestionCount)
        return ExamTemplate(
            name: "İnönü Sabit Sınav Şablonu v1",
            courseTitle: "Yapay Zekâ",
            studentNameRegion: NormalizedRect(x: 0.19, y: 0.115, width: 0.55, height: 0.055),
            totalScoreRegion: NormalizedRect(x: 0.78, y: 0.205, width: 0.14, height: 0.055),
            questions: (1 ... count).map { question(number: $0) }
        )
    }

    public mutating func setQuestionCount(_ requestedCount: Int) {
        let count = min(max(requestedCount, 1), Self.maximumQuestionCount)
        if count < questions.count {
            questions.removeLast(questions.count - count)
        } else if count > questions.count {
            for number in (questions.count + 1) ... count {
                questions.append(Self.question(number: number))
            }
        }
        for index in questions.indices {
            questions[index].number = index + 1
            questions[index].scoreRegion = Self.scoreRegion(questionNumber: index + 1)
        }
    }

    public var maximumTotalScore: Double {
        questions.reduce(0) { $0 + $1.maximumScore }
    }

    private static func question(number: Int) -> ExamQuestionTemplate {
        ExamQuestionTemplate(
            number: number,
            maximumScore: 20,
            programOutcome: "PÇ\(number)",
            scoreRegion: scoreRegion(questionNumber: number)
        )
    }

    private static func scoreRegion(questionNumber: Int) -> NormalizedRect {
        NormalizedRect(
            x: 0.78,
            y: 0.29 + (Double(questionNumber - 1) * 0.052),
            width: 0.14,
            height: 0.045
        )
    }
}

public enum ConfidenceLevel: String, Codable, CaseIterable, Sendable {
    case high
    case medium
    case low

    public init(score: Double) {
        if score >= 0.85 {
            self = .high
        } else if score >= 0.60 {
            self = .medium
        } else {
            self = .low
        }
    }

    public var title: String {
        switch self {
        case .high: "Yüksek güven"
        case .medium: "Kontrol önerilir"
        case .low: "Kontrol gerekli"
        }
    }
}

public struct RecognizedField: Codable, Hashable, Sendable {
    public var value: String
    public let confidence: Double

    public init(value: String, confidence: Double) {
        self.value = value
        self.confidence = min(max(confidence, 0), 1)
    }

    public var level: ConfidenceLevel { ConfidenceLevel(score: confidence) }
}

public struct QuestionRecognition: Identifiable, Codable, Hashable, Sendable {
    public let id: UUID
    public let number: Int
    public let programOutcome: String
    public let maximumScore: Double
    public var score: RecognizedField

    public init(
        id: UUID = UUID(),
        number: Int,
        programOutcome: String,
        maximumScore: Double,
        score: RecognizedField
    ) {
        self.id = id
        self.number = number
        self.programOutcome = programOutcome
        self.maximumScore = maximumScore
        self.score = score
    }
}

public struct ExamRecognition: Codable, Hashable, Sendable {
    public let templateName: String
    public let courseTitle: String
    public var studentName: RecognizedField
    public var totalScore: RecognizedField
    public var questions: [QuestionRecognition]

    public var calculatedTotal: Double {
        questions.reduce(0) { partial, question in
            partial + (Double(question.score.value.replacingOccurrences(of: ",", with: ".")) ?? 0)
        }
    }

}
