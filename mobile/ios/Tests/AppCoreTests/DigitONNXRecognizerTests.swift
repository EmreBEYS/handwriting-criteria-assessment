import Foundation
import CoreGraphics
import Testing
@testable import AppCore

@Test func preprocessingMatchesRustReferenceFixtures() throws {
    for fixture in try recognizerFixtures() {
        let input = DigitRecognizerContract.preprocess(fixture.image)
        #expect(input.width == fixture.tensorWidth, Comment(rawValue: fixture.file))
        let sum = input.values.reduce(0) { $0 + Double($1) }
        #expect(abs(sum - fixture.tensorSum) < 0.05, Comment(rawValue: fixture.file))
    }
}

@Test func bundledONNXModelMatchesRustReferenceAndCompletesBenchmarkBatch() throws {
    let recognizer = try ONNXDigitRecognizer()
    let fixtures = try recognizerFixtures()
    let started = Date()
    for fixture in fixtures {
        let reading = try recognizer.recognize(fixture.image, kind: fixture.kind)
        #expect(reading.text == fixture.expectedText, Comment(rawValue: fixture.file))
        #expect(
            abs(reading.confidence - fixture.expectedConfidence) < 0.002,
            Comment(rawValue: fixture.file)
        )
    }
    let duration = Date().timeIntervalSince(started)
    #expect(duration < 60, "15-cell benchmark took \(duration) seconds")
}

@Test func ctcDecoderFiltersKindsAndUsesWeakestFrameForConfidence() {
    let classes = DigitRecognizerContract.alphabet.count + 1
    func frame(_ index: Int, _ probability: Float) -> [Float] {
        var values = [Float](repeating: (1 - probability) / Float(classes - 1), count: classes)
        values[index] = probability
        return values
    }
    let path = [(0, 0.99), (2, 0.9), (2, 0.95), (0, 0.6), (2, 0.9),
                (8, 0.97), (11, 0.9), (6, 0.9), (12, 0.8)]
    let probabilities = path.flatMap { frame($0.0, Float($0.1)) }
    let score = DigitRecognizerContract.decode(probabilities: probabilities, classes: classes)
    #expect(score.text == "117.5~")
    #expect(abs(score.confidence - 0.6) < 0.0001)

    let number = DigitRecognizerContract.decode(
        probabilities: probabilities,
        classes: classes,
        allowedCharacters: "0123456789"
    )
    #expect(number.text == "1175")
    #expect(number.confidence < 0.1)
}

@Test func calibratedConfidenceAndFallbackRequireHumanReview() {
    #expect(!RecognizedField(value: "18", confidence: 0.99, source: .onnxDigitCRNN).requiresReview)
    #expect(RecognizedField(value: "18", confidence: 0.989, source: .onnxDigitCRNN).requiresReview)
    #expect(RecognizedField(value: "~18", confidence: 0.999, source: .onnxDigitCRNN).requiresReview)
    #expect(RecognizedField(value: "18", confidence: 0.59, source: .appleVisionFallback).requiresReview)
}

@Test func normalizedCropUsesTopLeftTemplateCoordinates() throws {
    // RGBA rows: red, green / blue, white.
    let pixels: [UInt8] = [
        255, 0, 0, 255, 0, 255, 0, 255,
        0, 0, 255, 255, 255, 255, 255, 255,
    ]
    let provider = try #require(CGDataProvider(data: Data(pixels) as CFData))
    let image = try #require(CGImage(
        width: 2,
        height: 2,
        bitsPerComponent: 8,
        bitsPerPixel: 32,
        bytesPerRow: 8,
        space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedLast.rawValue)
            .union(.byteOrder32Big),
        provider: provider,
        decode: nil,
        shouldInterpolate: false,
        intent: .defaultIntent
    ))
    let topLeft = try ONNXDigitRecognizer.crop(
        image: image,
        region: NormalizedRect(x: 0, y: 0, width: 0.5, height: 0.5)
    )
    #expect(topLeft.width == 1)
    #expect(topLeft.height == 1)
    #expect(topLeft.pixels == [255, 0, 0])
}

private struct RecognizerFixture {
    let file: String
    let image: RGBCellImage
    let kind: DigitFieldKind
    let tensorWidth: Int
    let tensorSum: Double
    let expectedText: String
    let expectedConfidence: Double
}

private func recognizerFixtures() throws -> [RecognizerFixture] {
    let directory = try #require(
        Bundle.module.url(forResource: "RecognizerFixtures", withExtension: nil)
    )
    let expectedURL = directory.appendingPathComponent("expected.tsv")
    let lines = try String(contentsOf: expectedURL, encoding: .utf8)
        .split(separator: "\n", omittingEmptySubsequences: false)
        .dropFirst()
    return try lines.compactMap { line in
        guard !line.isEmpty else { return nil }
        let fields = line.split(separator: "\t", omittingEmptySubsequences: false).map(String.init)
        let file = fields[0]
        let width = try #require(Int(fields[1]))
        let height = try #require(Int(fields[2]))
        let kind: DigitFieldKind = switch fields[3] {
        case "score": .score
        case "total": .declaredTotal
        default: .studentNumber
        }
        let pixels = [UInt8](try Data(contentsOf: directory.appendingPathComponent(file)))
        return RecognizerFixture(
            file: file,
            image: try RGBCellImage(width: width, height: height, pixels: pixels),
            kind: kind,
            tensorWidth: try #require(Int(fields[5])),
            tensorSum: try #require(Double(fields[6])),
            expectedText: fields[7],
            expectedConfidence: try #require(Double(fields[8]))
        )
    }
}
