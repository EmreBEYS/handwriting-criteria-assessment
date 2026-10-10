import ImageIO
import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

struct CaptureUploadView: View {
    let api: APIClient
    let selection: ExamSelection
    let onUploaded: (UUID) -> Void

    @State private var selectedPhoto: PhotosPickerItem?
    @State private var imageData: Data?
    @State private var clientRequestID = UUID()
    @State private var isUploading = false
    @State private var errorMessage: String?
#if os(iOS)
    @State private var showsCamera = false
#endif

    var body: some View {
        ZStack {
            AppBackground()
            ScrollView {
                VStack(spacing: 22) {
                    ScreenTitle(
                        eyebrow: "Yeni Tarama",
                        title: "Kâğıdı hazırla",
                        subtitle: "Net, gölgesiz ve formun tamamının göründüğü bir fotoğraf kullanın."
                    )
                    AppCard {
                        HStack(spacing: 14) {
                            IconBadge(systemName: "doc.text.fill")
                            VStack(alignment: .leading, spacing: 4) {
                                Text(selection.courseTitle)
                                    .font(.headline)
                                Text(selection.examTitle)
                                    .foregroundStyle(InonuTheme.textSecondary)
                            }
                        }
                    }
                    AppCard {
                        VStack(spacing: 16) {
                            ZStack {
                                RoundedRectangle(cornerRadius: 20, style: .continuous)
                                    .fill(InonuTheme.elevatedSurface)
                                    .frame(height: 170)
                                VStack(spacing: 12) {
                                    Image(
                                        systemName: imageData == nil
                                            ? "doc.viewfinder" : "checkmark.circle.fill"
                                    )
                                    .font(.system(size: 48, weight: .light))
                                    .foregroundStyle(
                                        imageData == nil ? InonuTheme.sky : InonuTheme.turquoise
                                    )
                                    Text(
                                        imageData == nil
                                            ? "Sınav kâğıdı görseli bekleniyor"
                                            : "Görsel yüklemeye hazır"
                                    )
                                    .font(.headline)
                                    if let imageData {
                                        Text("\(imageData.count / 1024) KB • JPEG")
                                            .font(.caption)
                                            .foregroundStyle(InonuTheme.textSecondary)
                                    }
                                }
                            }
                            PhotosPicker(selection: $selectedPhoto, matching: .images) {
                                Label(
                                    "Fotoğraf Arşivinden Seç",
                                    systemImage: "photo.on.rectangle"
                                )
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .background(InonuTheme.elevatedSurface)
                                .clipShape(RoundedRectangle(cornerRadius: 15))
                                .overlay {
                                    RoundedRectangle(cornerRadius: 15)
                                        .stroke(InonuTheme.border, lineWidth: 1)
                                }
                            }
                            .foregroundStyle(InonuTheme.sky)
#if os(iOS)
                            Button {
                                showsCamera = true
                            } label: {
                                Label("Kamera ile Çek", systemImage: "camera.fill")
                            }
                            .buttonStyle(SecondaryActionButtonStyle())
#endif
                        }
                    }
                    if let errorMessage {
                        AppCard {
                            Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                                .foregroundStyle(InonuTheme.danger)
                        }
                    }
                    Button {
                        Task { await upload() }
                    } label: {
                        if isUploading {
                            ProgressView().tint(InonuTheme.deepBlue)
                        } else {
                            Label("Yükle ve Analizi Başlat", systemImage: "arrow.up.doc.fill")
                        }
                    }
                    .buttonStyle(PrimaryActionButtonStyle())
                    .disabled(imageData == nil || isUploading)
                    .opacity(imageData == nil || isUploading ? 0.5 : 1)
                }
                .padding(20)
            }
        }
        .navigationTitle("Kâğıt Yükle")
        .inonuNavigationChrome()
        .preferredColorScheme(.dark)
        .onChange(of: selectedPhoto) { item in
            guard let item else { return }
            Task { await loadPhoto(item) }
        }
#if os(iOS)
        .sheet(isPresented: $showsCamera) {
            CameraPicker { data in imageData = data }
        }
#endif
    }

    private func loadPhoto(_ item: PhotosPickerItem) async {
        do {
            guard let source = try await item.loadTransferable(type: Data.self),
                  let jpeg = normalizedJPEG(source)
            else {
                throw APIClientError.transport("Seçilen görsel okunamadı.")
            }
            imageData = jpeg
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func upload() async {
        guard let imageData else { return }
        isUploading = true
        defer { isUploading = false }
        do {
            let scan = try await api.uploadScan(
                examID: selection.examID,
                imageData: imageData,
                clientRequestID: clientRequestID
            )
            onUploaded(scan.id)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func normalizedJPEG(_ data: Data) -> Data? {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
              let output = CFDataCreateMutable(nil, 0),
              let destination = CGImageDestinationCreateWithData(
                  output,
                  UTType.jpeg.identifier as CFString,
                  1,
                  nil
              )
        else { return nil }
        CGImageDestinationAddImage(
            destination,
            image,
            [kCGImageDestinationLossyCompressionQuality: 0.9] as CFDictionary
        )
        guard CGImageDestinationFinalize(destination) else { return nil }
        return output as Data
    }
}

#if os(iOS)
import UIKit

private struct CameraPicker: UIViewControllerRepresentable {
    let onCapture: (Data) -> Void
    @Environment(\.dismiss) private var dismiss

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    final class Coordinator: NSObject, UINavigationControllerDelegate, UIImagePickerControllerDelegate {
        let parent: CameraPicker

        init(parent: CameraPicker) {
            self.parent = parent
        }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            if let image = info[.originalImage] as? UIImage,
               let data = image.jpegData(compressionQuality: 0.9)
            {
                parent.onCapture(data)
            }
            parent.dismiss()
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
        }
    }
}
#endif
