import CoreGraphics
import Foundation
import OnnxRuntimeBindings

public enum DigitFieldKind: Sendable {
    case score
    case declaredTotal
    case studentNumber

    var allowedCharacters: String {
        switch self {
        case .score, .declaredTotal: DigitRecognizerContract.alphabet
        case .studentNumber: "0123456789"
        }
    }
}

public struct RGBCellImage: Sendable {
    public let width: Int
    public let height: Int
    public let pixels: [UInt8]

    public init(width: Int, height: Int, pixels: [UInt8]) throws {
        guard width > 0, height > 0, pixels.count == width * height * 3 else {
            throw DigitRecognizerError.invalidImage
        }
        self.width = width
        self.height = height
        self.pixels = pixels
    }
}

public struct DigitModelInput: Sendable {
    public let width: Int
    public let values: [Float]
}

public struct DigitReading: Hashable, Sendable {
    public let text: String
    public let confidence: Double

    public var valueText: String { text.replacingOccurrences(of: "~", with: "") }
    public var hasCorrection: Bool { text.contains("~") }
    public var isBlank: Bool { text.isEmpty }
}

public enum DigitRecognizerError: LocalizedError {
    case invalidImage
    case missingModel
    case invalidModelOutput

    public var errorDescription: String? {
        switch self {
        case .invalidImage: "Rakam hücresi görseli geçersiz."
        case .missingModel: "Rakam tanıma modeli uygulama paketinde bulunamadı."
        case .invalidModelOutput: "Rakam tanıma modeli beklenmeyen bir çıktı üretti."
        }
    }
}

/// Swift implementation of the source recognizer's Rust/Python contract.
/// Keep constants and rounding behavior in sync with the documented source commit.
public enum DigitRecognizerContract {
    public static let alphabet = "0123456789.~"
    public static let inputHeight = 32
    public static let minimumWidth = 16
    public static let maximumWidth = 512
    public static let widthMultiple = 4
    public static let frameStride = 4
    public static let automaticAcceptanceThreshold = 0.99

    public static func preprocess(_ image: RGBCellImage) -> DigitModelInput {
        let scaled = Int(floor(Double(image.width * inputHeight) / Double(image.height) + 0.5))
        let resizedWidth = min(max(scaled, minimumWidth), maximumWidth)
        let paddedWidth = ((resizedWidth + widthMultiple - 1) / widthMultiple) * widthMultiple

        func samplePosition(_ position: Int, target: Int, source: Int) -> (Int, Int, Float) {
            let coordinate = min(
                max((Double(position) + 0.5) * Double(source) / Double(target) - 0.5, 0),
                Double(source - 1)
            )
            let low = Int(floor(coordinate))
            return (low, min(low + 1, source - 1), Float(coordinate - Double(low)))
        }

        let rows = (0 ..< inputHeight).map {
            samplePosition($0, target: inputHeight, source: image.height)
        }
        let columns = (0 ..< resizedWidth).map {
            samplePosition($0, target: resizedWidth, source: image.width)
        }
        var values = [Float](repeating: 1, count: 3 * inputHeight * paddedWidth)
        for channel in 0 ..< 3 {
            for (y, row) in rows.enumerated() {
                for (x, column) in columns.enumerated() {
                    func source(_ sourceX: Int, _ sourceY: Int) -> Float {
                        Float(image.pixels[(sourceY * image.width + sourceX) * 3 + channel])
                    }
                    let top = source(column.0, row.0) * (1 - column.2)
                        + source(column.1, row.0) * column.2
                    let bottom = source(column.0, row.1) * (1 - column.2)
                        + source(column.1, row.1) * column.2
                    let pixel = top * (1 - row.2) + bottom * row.2
                    values[(channel * inputHeight + y) * paddedWidth + x] = pixel / 127.5 - 1
                }
            }
        }
        return DigitModelInput(width: paddedWidth, values: values)
    }

    public static func decode(
        probabilities: [Float],
        classes: Int,
        allowedCharacters: String = alphabet
    ) -> DigitReading {
        guard classes > 1 else { return DigitReading(text: "", confidence: 0) }
        let characters = Array(alphabet)
        let usable = (0 ..< classes).map { index in
            index == 0 || (index - 1 < characters.count && allowedCharacters.contains(characters[index - 1]))
        }
        var text = ""
        var confidence: Float = probabilities.isEmpty ? 0 : 1
        var previous = 0
        for start in stride(from: 0, to: probabilities.count - probabilities.count % classes, by: classes) {
            var bestIndex = 0
            var bestProbability = -Float.greatestFiniteMagnitude
            for index in 0 ..< classes where usable[index] {
                let probability = probabilities[start + index]
                if probability > bestProbability {
                    bestIndex = index
                    bestProbability = probability
                }
            }
            confidence = min(confidence, bestProbability)
            if bestIndex != 0, bestIndex != previous, bestIndex - 1 < characters.count {
                text.append(characters[bestIndex - 1])
            }
            previous = bestIndex
        }
        return DigitReading(text: text, confidence: Double(confidence))
    }
}

public final class ONNXDigitRecognizer: @unchecked Sendable {
    public static let modelName = "digit-crnn-v3"
    public static let modelVersion = "3"
    public static let modelSHA256 = "84db44945e13991f71fa77e891f6fa5a050c1feba7a1327310e3dc0b05011052"

    private let session: ORTSession
    private let lock = NSLock()

    public init(modelURL: URL) throws {
        let environment = try ORTEnv(loggingLevel: .warning)
        let options = try ORTSessionOptions()
        try options.setGraphOptimizationLevel(.all)
        session = try ORTSession(
            env: environment,
            modelPath: modelURL.path,
            sessionOptions: options
        )
    }

    public convenience init() throws {
        guard let modelURL = Self.bundledModelURL else { throw DigitRecognizerError.missingModel }
        try self.init(modelURL: modelURL)
    }

    public static var bundledModelURL: URL? {
#if SWIFT_PACKAGE
        Bundle.module.url(forResource: modelName, withExtension: "onnx")
#else
        Bundle.main.url(forResource: modelName, withExtension: "onnx")
#endif
    }

    public func recognize(_ image: RGBCellImage, kind: DigitFieldKind) throws -> DigitReading {
        let input = DigitRecognizerContract.preprocess(image)
        let inputData = input.values.withUnsafeBytes {
            NSMutableData(bytes: $0.baseAddress!, length: $0.count)
        }
        let inputValue = try ORTValue(
            tensorData: inputData,
            elementType: .float,
            shape: [
                NSNumber(value: 1),
                NSNumber(value: 3),
                NSNumber(value: DigitRecognizerContract.inputHeight),
                NSNumber(value: input.width),
            ]
        )
        let outputs: [String: ORTValue] = try lock.withLock {
            try session.run(
                withInputs: ["image": inputValue],
                outputNames: ["probabilities"],
                runOptions: nil
            )
        }
        guard let output = outputs["probabilities"] else {
            throw DigitRecognizerError.invalidModelOutput
        }
        let shape = try output.tensorTypeAndShapeInfo().shape.map(\.intValue)
        guard shape.count == 3,
              shape[0] == 1,
              shape[1] == input.width / DigitRecognizerContract.frameStride,
              shape[2] == DigitRecognizerContract.alphabet.count + 1
        else { throw DigitRecognizerError.invalidModelOutput }
        let outputData = try output.tensorData()
        let buffer = UnsafeBufferPointer(
            start: outputData.bytes.assumingMemoryBound(to: Float.self),
            count: outputData.length / MemoryLayout<Float>.stride
        )
        let probabilities = Array(buffer)
        return DigitRecognizerContract.decode(
            probabilities: probabilities,
            classes: shape[2],
            allowedCharacters: kind.allowedCharacters
        )
    }

    public func recognize(image: CGImage, region: NormalizedRect, kind: DigitFieldKind) throws -> DigitReading {
        try recognize(Self.crop(image: image, region: region), kind: kind)
    }

    static func crop(image: CGImage, region: NormalizedRect) throws -> RGBCellImage {
        let bounds = CGRect(x: 0, y: 0, width: image.width, height: image.height)
        let requested = CGRect(
            x: region.x * Double(image.width),
            y: region.y * Double(image.height),
            width: region.width * Double(image.width),
            height: region.height * Double(image.height)
        ).integral.intersection(bounds)
        guard !requested.isNull,
              requested.width >= 1,
              requested.height >= 1,
              let cropped = image.cropping(to: requested)
        else { throw DigitRecognizerError.invalidImage }

        let width = cropped.width
        let height = cropped.height
        var rgba = [UInt8](repeating: 255, count: width * height * 4)
        guard let context = CGContext(
            data: &rgba,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue | CGBitmapInfo.byteOrder32Big.rawValue
        ) else { throw DigitRecognizerError.invalidImage }
        context.interpolationQuality = .none
        context.translateBy(x: 0, y: CGFloat(height))
        context.scaleBy(x: 1, y: -1)
        context.draw(cropped, in: CGRect(x: 0, y: 0, width: width, height: height))
        var rgb = [UInt8]()
        rgb.reserveCapacity(width * height * 3)
        for index in stride(from: 0, to: rgba.count, by: 4) {
            rgb.append(contentsOf: rgba[index ..< index + 3])
        }
        return try RGBCellImage(width: width, height: height, pixels: rgb)
    }
}
