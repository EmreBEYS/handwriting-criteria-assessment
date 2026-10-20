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
    private static let bundledDigitRecognizer = try? ONNXDigitRecognizer()
    private let digitRecognizer: ONNXDigitRecognizer?

    public init() {
        digitRecognizer = Self.bundledDigitRecognizer
    }

    public init(digitRecognizer: ONNXDigitRecognizer?) {
        self.digitRecognizer = digitRecognizer
    }

    public func recognize(imageData: Data, template: ExamTemplate) async throws -> ExamRecognition {
#if canImport(Vision)
        guard let source = CGImageSourceCreateWithData(imageData as CFData, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil)
        else { throw ExamReaderError.invalidImage }

        return try await Task.detached(priority: .userInitiated) {
            let student = try Self.recognizeText(in: template.studentNameRegion, image: image)
            let total = try Self.recognizeNumeric(
                in: template.totalScoreRegion,
                image: image,
                kind: .declaredTotal,
                maximum: template.maximumTotalScore,
                digitRecognizer: digitRecognizer
            )
            let questions = try template.questions.map { question in
                let field = try Self.recognizeNumeric(
                    in: question.scoreRegion,
                    image: image,
                    kind: .score,
                    maximum: question.maximumScore,
                    digitRecognizer: digitRecognizer
                )
                return QuestionRecognition(
                    number: question.number,
                    programOutcome: question.programOutcome,
                    maximumScore: question.maximumScore,
                    score: field
                )
            }
            return ExamRecognition(
                templateName: template.name,
                courseTitle: template.courseTitle,
                studentName: student,
                totalScore: total,
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
            confidence: Double(candidates.map(\.confidence).min() ?? 0),
            source: .appleVisionText
        )
    }

    private static func recognizeNumeric(
        in region: NormalizedRect,
        image: CGImage,
        kind: DigitFieldKind,
        maximum: Double,
        digitRecognizer: ONNXDigitRecognizer?
    ) throws -> RecognizedField {
        if let digitRecognizer {
            do {
                let reading = try digitRecognizer.recognize(image: image, region: region, kind: kind)
                return normalizedScore(
                    RecognizedField(
                        value: reading.valueText,
                        confidence: reading.confidence,
                        source: .onnxDigitCRNN
                    ),
                    maximum: maximum,
                    correctionDetected: reading.hasCorrection
                )
            } catch {
                // Keep the scanner usable if the embedded runtime/model fails,
                // but never auto-accept the legacy OCR fallback.
            }
        }
        let fallback = try recognizeText(in: region, image: image)
        return normalizedScore(
            RecognizedField(
                value: fallback.value,
                confidence: min(fallback.confidence, 0.59),
                source: .appleVisionFallback
            ),
            maximum: maximum
        )
    }

    private static func normalizedScore(
        _ field: RecognizedField,
        maximum: Double,
        correctionDetected: Bool = false
    ) -> RecognizedField {
        let allowed = field.value.filter { $0.isNumber || $0 == "," || $0 == "." }
        guard let parsed = Double(allowed.replacingOccurrences(of: ",", with: ".")),
              parsed >= 0,
              parsed <= maximum
        else {
            return RecognizedField(
                value: correctionDetected ? "~\(allowed)" : allowed,
                confidence: min(field.confidence, 0.3),
                source: field.source
            )
        }
        return RecognizedField(
            value: correctionDetected ? "~\(Self.format(parsed))" : Self.format(parsed),
            confidence: field.confidence,
            source: field.source
        )
    }

    private static func format(_ value: Double) -> String {
        value.rounded() == value ? String(Int(value)) : String(format: "%.2f", value)
    }
#endif
}
