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
    @State private var isUploading = false
    @State private var errorMessage: String?
#if os(iOS)
    @State private var showsCamera = false
#endif

    var body: some View {
        Form {
            Section("Sınav") {
                Text(selection.courseTitle)
                Text(selection.examTitle).foregroundStyle(.secondary)
            }
            Section("Kâğıt Görseli") {
                PhotosPicker(selection: $selectedPhoto, matching: .images) {
                    Label("Fotoğraf Arşivinden Seç", systemImage: "photo.on.rectangle")
                }
#if os(iOS)
                Button {
                    showsCamera = true
                } label: {
                    Label("Kamera ile Çek", systemImage: "camera")
                }
#endif
                if let imageData {
                    Label(
                        "Görsel hazır (\(imageData.count / 1024) KB)",
                        systemImage: "checkmark.circle.fill"
                    )
                    .foregroundStyle(.green)
                }
            }
            if let errorMessage {
                Text(errorMessage).foregroundStyle(.red)
            }
            Button {
                Task { await upload() }
            } label: {
                if isUploading {
                    ProgressView().frame(maxWidth: .infinity)
                } else {
                    Text("Yükle ve Analizi Başlat").frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(imageData == nil || isUploading)
        }
        .navigationTitle("Kâğıt Yükle")
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
            let scan = try await api.uploadScan(examID: selection.examID, imageData: imageData)
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
