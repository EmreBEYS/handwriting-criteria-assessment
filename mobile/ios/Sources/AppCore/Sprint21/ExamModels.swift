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

    /// Coordinates measured from the supplied "Yapay Zeka 2026-Final -A"
    /// sheet. They use a top-left origin after VisionKit page correction.
    public static func inonuFixedV1() -> ExamTemplate {
        let scoreRegions = [
            NormalizedRect(x: 0.167484, y: 0.266414, width: 0.091503, height: 0.020202),
            NormalizedRect(x: 0.258987, y: 0.266414, width: 0.091667, height: 0.020202),
            NormalizedRect(x: 0.350654, y: 0.266414, width: 0.091667, height: 0.020202),
            NormalizedRect(x: 0.442320, y: 0.266414, width: 0.090523, height: 0.020202),
        ]
        let outcomes = ["PÇ2", "PÇ1", "PÇ3", "PÇ2"]
        return ExamTemplate(
            name: "İnönü Sabit Sınav Şablonu v1",
            courseTitle: "Yapay Zekâ",
            studentNameRegion: NormalizedRect(x: 0.578431, y: 0.110859, width: 0.231536, height: 0.024495),
            totalScoreRegion: NormalizedRect(x: 0.167484, y: 0.286616, width: 0.365359, height: 0.020202),
            questions: scoreRegions.indices.map { index in
                ExamQuestionTemplate(
                    number: index + 1,
                    maximumScore: 20,
                    programOutcome: outcomes[index],
                    scoreRegion: scoreRegions[index]
                )
            }
        )
    }

    public var maximumTotalScore: Double {
        questions.reduce(0) { $0 + $1.maximumScore }
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

public enum RecognitionSource: String, Codable, Sendable {
    case onnxDigitCRNN = "digit-crnn-v3"
    case appleVisionText = "apple-vision-text"
    case appleVisionFallback = "apple-vision-fallback"
}

public struct RecognizedField: Codable, Hashable, Sendable {
    public var value: String
    public let confidence: Double
    public let source: RecognitionSource

    public init(
        value: String,
        confidence: Double,
        source: RecognitionSource = .appleVisionText
    ) {
        self.value = value
        self.confidence = min(max(confidence, 0), 1)
        self.source = source
    }

    public var level: ConfidenceLevel { ConfidenceLevel(score: confidence) }

    /// The CRNN was calibrated at 0.99 for automatic acceptance. Blank and
    /// crossed-out fields always need an instructor even when confidence is high.
    public var requiresReview: Bool {
        value.isEmpty
            || value.contains("~")
            || (source == .onnxDigitCRNN && confidence < DigitRecognizerContract.automaticAcceptanceThreshold)
            || source == .appleVisionFallback
            || confidence < 0.60
    }
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
        calculatedTotalIfComplete ?? 0
    }

    /// A missing OCR value is not a zero score. Keep the total absent until
    /// every printed score cell has a numeric value.
    public var calculatedTotalIfComplete: Double? {
        let values = questions.compactMap {
            Double($0.score.value.replacingOccurrences(of: ",", with: "."))
        }
        guard values.count == questions.count else { return nil }
        return values.reduce(0, +)
    }

    public var requiresReview: Bool {
        guard let declaredTotal = Double(totalScore.value.replacingOccurrences(of: ",", with: ".")) else {
            return true
        }
        guard let calculatedTotal = calculatedTotalIfComplete else { return true }
        return studentName.requiresReview
            || totalScore.requiresReview
            || questions.contains { $0.score.requiresReview }
            || abs(calculatedTotal - declaredTotal) > 0.001
    }

    public var reviewFieldCount: Int {
        [studentName, totalScore].filter(\.requiresReview).count
            + questions.map(\.score).filter(\.requiresReview).count
    }

}
