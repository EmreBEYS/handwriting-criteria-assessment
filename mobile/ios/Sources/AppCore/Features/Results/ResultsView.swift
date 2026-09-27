import SwiftUI

struct ResultsView: View {
    let onDone: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "chart.bar.doc.horizontal")
                .font(.system(size: 56))
                .accessibilityHidden(true)
            Text("No Results Yet")
                .font(.title2.bold())
            Text("Result components will be defined after criteria and labels are approved.")
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Done", action: onDone)
                .buttonStyle(.borderedProminent)
        }
        .padding()
        .navigationTitle("Results")
        .navigationBarBackButtonHidden()
    }
}
