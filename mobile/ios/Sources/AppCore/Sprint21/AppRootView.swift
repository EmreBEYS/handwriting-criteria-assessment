import SwiftUI
import UniformTypeIdentifiers

public struct AppRootView: View {
    @State private var template = ExamTemplate.inonuFixedV1()
    @State private var showsScanner = false
    @State private var isRecognizing = false
    @State private var results: [ExamRecognition] = []
    @State private var exportsFile = false
    @State private var errorMessage: String?

    public init() {}

    public var body: some View {
        NavigationStack {
            ZStack {
                AppBackground()
                ScrollView {
                    VStack(spacing: 20) {
                        ScreenTitle(
                            eyebrow: "Sprint 00-22",
                            title: "Seri sınav kâğıdı tara",
                            subtitle: "Her sayfayı otomatik oku ve aynı renkli Excel tablosuna yeni satır olarak ekle."
                        )
                        templateCard
                        questionsCard
                        if !results.isEmpty {
                            resultsCard
                        }
                        if let errorMessage {
                            AppCard {
                                Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                                    .foregroundStyle(InonuTheme.danger)
                            }
                        }
                        Button {
                            showsScanner = true
                        } label: {
                            Label(results.isEmpty ? "Kâğıtları Tara" : "Yeni Kâğıtlar Ekle", systemImage: "doc.viewfinder")
                        }
                        .buttonStyle(PrimaryActionButtonStyle())
                        .disabled(!documentScannerAvailable)
#if !os(iOS)
                        Text("Belge kamerası iPhone veya iPad üzerinde kullanılabilir.")
                            .font(.caption)
                            .foregroundStyle(InonuTheme.textSecondary)
#endif
                    }
                    .padding(20)
                }
                if isRecognizing {
                    ProgressView("Alanlar okunuyor…")
                        .padding(24)
                        .background(InonuTheme.surface)
                        .clipShape(RoundedRectangle(cornerRadius: 18))
                }
            }
            .navigationTitle("Kâğıt Okuma")
            .inonuNavigationChrome()
            .preferredColorScheme(.dark)
            .fileExporter(
                isPresented: $exportsFile,
                document: ExcelDocument(data: ExamExcelExporter.data(for: results)),
                contentType: excelContentType,
                defaultFilename: "sinav-sonuclari"
            ) { result in
                if case let .failure(error) = result {
                    errorMessage = error.localizedDescription
                }
            }
#if os(iOS)
            .sheet(isPresented: $showsScanner) {
                DocumentScannerView { imageDataList in
                    showsScanner = false
                    Task { await recognize(imageDataList) }
                } onCancel: {
                    showsScanner = false
                }
            }
#endif
        }
    }

    private var excelContentType: UTType {
        UTType(filenameExtension: "xlsx") ?? .data
    }

    private var documentScannerAvailable: Bool {
#if os(iOS)
        true
#else
        false
#endif
    }

    private var templateCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                Label(template.name, systemImage: "rectangle.and.text.magnifyingglass")
                    .font(.headline)
                TextField("Ders adı", text: $template.courseTitle)
                    .textFieldStyle(.roundedBorder)
                Label("Sabit dört puan hücresi", systemImage: "rectangle.grid.1x2")
                    .font(.subheadline.bold())
                Text("Ad-soyad, Not satırı ve S1–S4 puan hücreleri gönderilen Yapay Zeka 2026-Final A kâğıdına göre okunur.")
                    .font(.caption)
                    .foregroundStyle(InonuTheme.textSecondary)
            }
        }
    }

    private var questionsCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                Text("SORU–PÇ EŞLEŞMESİ")
                    .font(.caption.bold())
                    .tracking(1.1)
                    .foregroundStyle(InonuTheme.sky)
                ForEach($template.questions) { $question in
                    HStack {
                        Text("S\(question.number)").font(.headline).frame(width: 36)
                        TextField("PÇ", text: $question.programOutcome)
                            .textFieldStyle(.roundedBorder)
                        TextField(
                            "Azami",
                            value: $question.maximumScore,
                            format: .number.precision(.fractionLength(0 ... 2))
                        )
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 84)
                    }
                }
            }
        }
    }

    private var resultsCard: some View {
        AppCard {
            VStack(alignment: .leading, spacing: 14) {
                Label("\(results.count) kâğıt Excel tablosuna eklendi", systemImage: "tablecells.fill")
                    .font(.headline)
                    .foregroundStyle(InonuTheme.turquoise)
                let reviewCount = results.filter(\.requiresReview).count
                if reviewCount > 0 {
                    Label(
                        "\(reviewCount) kâğıtta model güveni, boş/düzeltilmiş alan veya toplam uyuşmazlığı nedeniyle kontrol gerekli",
                        systemImage: "person.crop.circle.badge.exclamationmark"
                    )
                    .font(.caption.bold())
                    .foregroundStyle(.yellow)
                }
                HStack(spacing: 8) {
                    ConfidenceLegend(title: "Yeşil", color: InonuTheme.turquoise)
                    ConfidenceLegend(title: "Sarı", color: .yellow)
                    ConfidenceLegend(title: "Kırmızı", color: InonuTheme.danger)
                }
                Text("Rakam hücreleri cihazdaki digit-crnn-v3 modeliyle okunur. 0,99 altı tahminler ve teknik yedek okumalar öğretim elemanı kontrolü ister; Excel renkleri güven düzeyini gösterir.")
                    .font(.caption)
                    .foregroundStyle(InonuTheme.textSecondary)
                Button {
                    exportsFile = true
                } label: {
                    Label("Güncel Excel Dosyasını Aç", systemImage: "square.and.arrow.up")
                }
                .buttonStyle(PrimaryActionButtonStyle())
            }
        }
    }

    @MainActor
    private func recognize(_ imageDataList: [Data]) async {
        isRecognizing = true
        errorMessage = nil
        defer { isRecognizing = false }
        var failures: [Int] = []
        for (index, imageData) in imageDataList.enumerated() {
            do {
                let recognition = try await VisionExamReader().recognize(
                    imageData: imageData,
                    template: template
                )
                results.append(recognition)
            } catch {
                failures.append(index + 1)
            }
        }
        if !failures.isEmpty {
            errorMessage = "\(failures.map(String.init).joined(separator: ", ")). sayfa okunamadı; diğerleri Excel'e eklendi."
        }
        if failures.count < imageDataList.count {
            exportsFile = true
        }
    }
}

private struct ConfidenceLegend: View {
    let title: String
    let color: Color
    var body: some View {
        Label(title, systemImage: "circle.fill")
            .font(.caption.bold())
            .foregroundStyle(color)
    }
}

private struct ExcelDocument: FileDocument {
    static var readableContentTypes: [UTType] { [UTType(filenameExtension: "xlsx") ?? .data] }
    let data: Data

    init(data: Data) { self.data = data }

    init(configuration: ReadConfiguration) throws {
        data = configuration.file.regularFileContents ?? Data()
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: data)
    }
}

#if os(iOS)
import VisionKit

private struct DocumentScannerView: UIViewControllerRepresentable {
    let onScan: ([Data]) -> Void
    let onCancel: () -> Void

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
        let controller = VNDocumentCameraViewController()
        controller.delegate = context.coordinator
        return controller
    }

    func updateUIViewController(_ controller: VNDocumentCameraViewController, context: Context) {}

    final class Coordinator: NSObject, @preconcurrency VNDocumentCameraViewControllerDelegate {
        let parent: DocumentScannerView

        init(parent: DocumentScannerView) { self.parent = parent }

        @MainActor func documentCameraViewController(
            _ controller: VNDocumentCameraViewController,
            didFinishWith scan: VNDocumentCameraScan
        ) {
            let pageData = (0 ..< scan.pageCount).compactMap {
                scan.imageOfPage(at: $0).jpegData(compressionQuality: 0.92)
            }
            guard !pageData.isEmpty else {
                parent.onCancel()
                return
            }
            parent.onScan(pageData)
        }

        @MainActor func documentCameraViewControllerDidCancel(
            _ controller: VNDocumentCameraViewController
        ) {
            parent.onCancel()
        }

        @MainActor func documentCameraViewController(
            _ controller: VNDocumentCameraViewController,
            didFailWithError error: Error
        ) {
            parent.onCancel()
        }
    }
}
#endif
