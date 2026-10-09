import SwiftUI

struct ResultsView: View {
    let result: ConfirmationResult
    let onDone: () -> Void

    var body: some View {
        ZStack {
            AppBackground()
            VStack(spacing: 24) {
                Spacer()
                ZStack {
                    Circle()
                        .fill(InonuTheme.turquoise.opacity(0.16))
                        .frame(width: 150, height: 150)
                    Circle()
                        .stroke(InonuTheme.turquoise, lineWidth: 2)
                        .frame(width: 118, height: 118)
                    Image(systemName: "checkmark")
                        .font(.system(size: 52, weight: .bold))
                        .foregroundStyle(InonuTheme.turquoise)
                }
                VStack(spacing: 8) {
                    Text("Okundu ve Kaydedildi")
                        .font(.title.bold())
                    Text("Öğretim elemanı onayı başarıyla tamamlandı.")
                        .foregroundStyle(InonuTheme.textSecondary)
                        .multilineTextAlignment(.center)
                }
                AppCard {
                    VStack(spacing: 18) {
                        Text("KESİN TOPLAM PUAN")
                            .font(.caption.bold())
                            .tracking(1.3)
                            .foregroundStyle(InonuTheme.sky)
                        Text("\(result.totalScore) / \(result.maximumTotalScore)")
                            .font(.system(size: 38, weight: .bold, design: .rounded))
                            .monospacedDigit()
                        Divider().overlay(InonuTheme.border)
                        HStack {
                            Label("Kayıt zamanı", systemImage: "clock.fill")
                                .foregroundStyle(InonuTheme.textSecondary)
                            Spacer()
                            Text(result.savedAt)
                                .font(.caption.monospaced())
                                .foregroundStyle(InonuTheme.textSecondary)
                        }
                    }
                }
                Button(action: onDone) {
                    Label("Yeni Kâğıt Okut", systemImage: "doc.viewfinder")
                }
                .buttonStyle(PrimaryActionButtonStyle())
                Spacer()
            }
            .padding(20)
        }
        .navigationTitle("Sonuç")
        .navigationBarBackButtonHidden()
        .inonuNavigationChrome()
        .preferredColorScheme(.dark)
    }
}
