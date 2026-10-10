import SwiftUI

struct ResultsView: View {
    let api: APIClient
    let result: ConfirmationResult
    let selection: ExamSelection
    let onDone: () -> Void

    @State private var analysis: ExamAnalysis?
    @State private var analysisError: String?
    @State private var isLoadingAnalysis = false

    var body: some View {
        ZStack {
            AppBackground()
            ScrollView {
              VStack(spacing: 24) {
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
                analysisSection
                Button(action: onDone) {
                    Label("Yeni Kâğıt Okut", systemImage: "doc.viewfinder")
                }
                .buttonStyle(PrimaryActionButtonStyle())
              }
              .padding(20)
            }
        }
        .navigationTitle("Sonuç")
        .navigationBarBackButtonHidden()
        .inonuNavigationChrome()
        .preferredColorScheme(.dark)
        .task { await loadAnalysis() }
    }

    @ViewBuilder
    private var analysisSection: some View {
        if isLoadingAnalysis {
            AppCard {
                HStack(spacing: 12) {
                    ProgressView().tint(InonuTheme.sky)
                    Text("PÇ sonuçları güncelleniyor…")
                }
            }
        } else if let analysis {
            AppCard {
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        IconBadge(systemName: "chart.bar.fill")
                        VStack(alignment: .leading, spacing: 3) {
                            Text("PÇ Sonuçları").font(.headline)
                            Text("\(analysis.confirmedPaperCount) onaylı kâğıt")
                                .font(.caption)
                                .foregroundStyle(InonuTheme.textSecondary)
                        }
                    }
                    if analysis.programOutcomes.isEmpty {
                        Text("Bu sınav için henüz PÇ eşlemesi bulunmuyor.")
                            .foregroundStyle(InonuTheme.textSecondary)
                    } else {
                        ForEach(analysis.programOutcomes) { outcome in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack {
                                    Text(outcome.code).font(.body.bold())
                                    Spacer()
                                    Text("%\(outcome.successPercentage)")
                                        .font(.body.bold().monospacedDigit())
                                        .foregroundStyle(InonuTheme.turquoise)
                                }
                                Text(outcome.description)
                                    .font(.caption)
                                    .foregroundStyle(InonuTheme.textSecondary)
                            }
                            if outcome.id != analysis.programOutcomes.last?.id {
                                Divider().overlay(InonuTheme.border)
                            }
                        }
                    }
                }
            }
        } else if let analysisError {
            AppCard {
                VStack(alignment: .leading, spacing: 12) {
                    Label("PÇ sonuçları alınamadı", systemImage: "exclamationmark.triangle.fill")
                        .foregroundStyle(InonuTheme.danger)
                    Text(analysisError)
                        .font(.caption)
                        .foregroundStyle(InonuTheme.textSecondary)
                    Button("Yeniden Dene") { Task { await loadAnalysis() } }
                        .buttonStyle(SecondaryActionButtonStyle())
                }
            }
        }
    }

    private func loadAnalysis() async {
        isLoadingAnalysis = true
        analysisError = nil
        defer { isLoadingAnalysis = false }
        do {
            analysis = try await api.examAnalysis(examID: selection.examID)
        } catch {
            analysisError = error.localizedDescription
        }
    }
}
