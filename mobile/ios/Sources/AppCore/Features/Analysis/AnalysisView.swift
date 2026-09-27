import SwiftUI

struct AnalysisView: View {
    let onShowResults: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            ProgressView()
            Text("Analysis Placeholder")
                .font(.title2.bold())
            Text("No model is connected. This screen only validates the navigation flow.")
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Show Placeholder Results", action: onShowResults)
                .buttonStyle(.borderedProminent)
        }
        .padding()
        .navigationTitle("Analysis")
    }
}
