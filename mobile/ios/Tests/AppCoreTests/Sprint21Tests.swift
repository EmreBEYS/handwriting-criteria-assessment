import Foundation
import Testing
@testable import AppCore

@Test func confidenceThresholdsUseTrafficLightBands() {
    #expect(ConfidenceLevel(score: 0.85) == .high)
    #expect(ConfidenceLevel(score: 0.849) == .medium)
    #expect(ConfidenceLevel(score: 0.60) == .medium)
    #expect(ConfidenceLevel(score: 0.599) == .low)
}

@Test func fixedTemplateMatchesProvidedPaper() {
    let template = ExamTemplate.inonuFixedV1()

    #expect(template.questions.count == 4)
    #expect(template.questions.map(\.number) == [1, 2, 3, 4])
    #expect(template.questions.map(\.programOutcome) == ["PÇ2", "PÇ1", "PÇ3", "PÇ2"])
    #expect(template.studentNameRegion == NormalizedRect(x: 0.578431, y: 0.110859, width: 0.231536, height: 0.024495))
    #expect(template.questions[0].scoreRegion == NormalizedRect(x: 0.167484, y: 0.266414, width: 0.091503, height: 0.020202))
    #expect(template.questions[3].scoreRegion == NormalizedRect(x: 0.442320, y: 0.266414, width: 0.090523, height: 0.020202))
    #expect(template.totalScoreRegion == NormalizedRect(x: 0.167484, y: 0.286616, width: 0.365359, height: 0.020202))
}

@Test func writtenAndCalculatedTotalsRemainSeparate() {
    let question = QuestionRecognition(
        number: 1,
        programOutcome: "PÇ1",
        maximumScore: 20,
        score: RecognizedField(value: "15", confidence: 0.95)
    )
    let result = ExamRecognition(
        templateName: "v1",
        courseTitle: "Yapay Zekâ",
        studentName: RecognizedField(value: "Ada Lovelace", confidence: 0.95),
        totalScore: RecognizedField(value: "14", confidence: 0.95),
        questions: [question]
    )

    #expect(result.calculatedTotal == 15)
    #expect(result.totalScore.value == "14")
}

@Test func missingQuestionScoreDoesNotBecomeCalculatedZero() {
    let result = ExamRecognition(
        templateName: "v1",
        courseTitle: "Yapay Zekâ",
        studentName: RecognizedField(value: "Ada", confidence: 0.95),
        totalScore: RecognizedField(value: "", confidence: 0),
        questions: [
            QuestionRecognition(
                number: 1,
                programOutcome: "PÇ2",
                maximumScore: 20,
                score: RecognizedField(value: "", confidence: 0, source: .onnxDigitCRNN)
            ),
        ]
    )

    #expect(result.calculatedTotalIfComplete == nil)
    let workbook = String(decoding: ExamExcelExporter.data(for: [result]), as: UTF8.self)
    #expect(workbook.contains("<c r=\"E5\" s=\"7\" t=\"inlineStr\"><is><t xml:space=\"preserve\"></t></is></c>"))
    #expect(!workbook.contains("<c r=\"E5\" s=\"1\" t=\"n\"><v>0.0</v></c>"))
}

@Test func excelWorkbookContainsRowsQuestionOutcomesAndTrafficLightStyles() {
    let firstResult = ExamRecognition(
        templateName: "Şablon v1",
        courseTitle: "Yapay Zekâ",
        studentName: RecognizedField(value: "Ada Lovelace", confidence: 0.92),
        totalScore: RecognizedField(value: "18", confidence: 0.91),
        questions: [
            QuestionRecognition(
                number: 1,
                programOutcome: "PÇ3",
                maximumScore: 20,
                score: RecognizedField(value: "18", confidence: 0.72)
            ),
        ]
    )
    let secondResult = ExamRecognition(
        templateName: "Şablon v1",
        courseTitle: "Yapay Zekâ",
        studentName: RecognizedField(value: "Alan Turing", confidence: 0.55),
        totalScore: RecognizedField(value: "20", confidence: 0.88),
        questions: [
            QuestionRecognition(
                number: 1,
                programOutcome: "PÇ3",
                maximumScore: 20,
                score: RecognizedField(value: "20", confidence: 0.93)
            ),
        ]
    )
    let data = ExamExcelExporter.data(for: [firstResult, secondResult])
    let workbookArchive = String(decoding: data, as: UTF8.self)

    #expect(data.starts(with: [0x50, 0x4B, 0x03, 0x04]))
    #expect(workbookArchive.contains("Ada Lovelace"))
    #expect(workbookArchive.contains("Alan Turing"))
    #expect(workbookArchive.contains("S1 (PÇ3)"))
    #expect(workbookArchive.contains("FFC6EFCE"))
    #expect(workbookArchive.contains("FFFFEB9C"))
    #expect(workbookArchive.contains("FFFFC7CE"))
    #expect(workbookArchive.contains("<c r=\"G5\" s=\"6\" t=\"n\"><v>18.0</v>"))
}
