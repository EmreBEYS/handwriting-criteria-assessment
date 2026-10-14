import CoreGraphics
import Foundation
import ImageIO

#if canImport(Vision)
import Vision
#endif

public enum ExamReaderError: LocalizedError {
    case invalidImage
    case recognitionUnavailable

    public var errorDescription: String? {
        switch self {
        case .invalidImage: "Taranan belge görseli okunamadı."
        case .recognitionUnavailable: "Bu cihazda metin tanıma kullanılamıyor."
        }
    }
}

public struct VisionExamReader: Sendable {
    public init() {}

    public func recognize(imageData: Data, template: ExamTemplate) async throws -> ExamRecognition {
#if canImport(Vision)
        guard let source = CGImageSourceCreateWithData(imageData as CFData, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil)
        else { throw ExamReaderError.invalidImage }

        return try await Task.detached(priority: .userInitiated) {
            let student = try Self.recognizeText(in: template.studentNameRegion, image: image)
            let total = try Self.recognizeText(in: template.totalScoreRegion, image: image)
            let questions = try template.questions.map { question in
                let field = try Self.recognizeText(in: question.scoreRegion, image: image)
                return QuestionRecognition(
                    number: question.number,
                    programOutcome: question.programOutcome,
                    maximumScore: question.maximumScore,
                    score: Self.normalizedScore(field, maximum: question.maximumScore)
                )
            }
            return ExamRecognition(
                templateName: template.name,
                courseTitle: template.courseTitle,
                studentName: student,
                totalScore: Self.normalizedScore(total, maximum: template.maximumTotalScore),
                questions: questions
            )
        }.value
#else
        throw ExamReaderError.recognitionUnavailable
#endif
    }

#if canImport(Vision)
    private static func recognizeText(in region: NormalizedRect, image: CGImage) throws -> RecognizedField {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = false
        request.recognitionLanguages = ["tr-TR", "en-US"]
        request.regionOfInterest = region.visionRegion
        try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
        let candidates = (request.results ?? []).compactMap { $0.topCandidates(1).first }
        guard !candidates.isEmpty else { return RecognizedField(value: "", confidence: 0) }
        return RecognizedField(
            value: candidates.map(\.string).joined(separator: " ").trimmingCharacters(in: .whitespaces),
            confidence: Double(candidates.map(\.confidence).min() ?? 0)
        )
    }

    private static func normalizedScore(_ field: RecognizedField, maximum: Double) -> RecognizedField {
        let allowed = field.value.filter { $0.isNumber || $0 == "," || $0 == "." }
        guard let parsed = Double(allowed.replacingOccurrences(of: ",", with: ".")),
              parsed >= 0,
              parsed <= maximum
        else { return RecognizedField(value: allowed, confidence: min(field.confidence, 0.3)) }
        return RecognizedField(value: Self.format(parsed), confidence: field.confidence)
    }

    private static func format(_ value: Double) -> String {
        value.rounded() == value ? String(Int(value)) : String(format: "%.2f", value)
    }
#endif
}
