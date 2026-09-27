import SwiftUI

struct CaptureUploadView: View {
    let onContinue: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "photo.on.rectangle.angled")
                .font(.system(size: 56))
                .accessibilityHidden(true)
            Text("Choose an Image")
                .font(.title2.bold())
            Text("Camera and photo-library integration will be connected after requirements are confirmed.")
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            HStack {
                Button("Capture") {}
                    .buttonStyle(.bordered)
                    .disabled(true)
                Button("Upload") {}
                    .buttonStyle(.bordered)
                    .disabled(true)
            }
            Button("Continue with Placeholder", action: onContinue)
                .buttonStyle(.borderedProminent)
        }
        .padding()
        .navigationTitle("Capture / Upload")
    }
}
