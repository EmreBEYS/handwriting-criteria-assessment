import SwiftUI

struct HomeView: View {
    let onStart: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "doc.text.viewfinder")
                .font(.system(size: 64))
                .accessibilityHidden(true)
            Text("Handwriting Assessment")
                .font(.largeTitle.bold())
                .multilineTextAlignment(.center)
            Text("Capture or upload a handwriting image to begin.")
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Start", action: onStart)
                .buttonStyle(.borderedProminent)
        }
        .padding()
        .navigationTitle("Home")
    }
}
