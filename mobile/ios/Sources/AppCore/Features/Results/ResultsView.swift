import SwiftUI

struct ResultsView: View {
    let result: ConfirmationResult
    let onDone: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 56))
                .foregroundStyle(.green)
                .accessibilityHidden(true)
            Text("Okundu ve Kaydedildi")
                .font(.title2.bold())
            Text("\(result.totalScore) / \(result.maximumTotalScore)")
                .font(.largeTitle.monospacedDigit())
            Text("Kayıt zamanı: \(result.savedAt)")
                .foregroundStyle(.secondary)
            Button("Yeni Kâğıt Okut", action: onDone)
                .buttonStyle(.borderedProminent)
        }
        .padding()
        .navigationTitle("Sonuç")
        .navigationBarBackButtonHidden()
    }
}
