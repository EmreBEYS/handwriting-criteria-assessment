import SwiftUI

struct HomeView: View {
    let api: APIClient
    let profile: UserProfile
    let onProfile: () -> Void
    let onStart: (ExamSelection) -> Void

    @State private var offerings: [CourseOffering] = []
    @State private var exams: [ExamSummary] = []
    @State private var selectedOfferingID: UUID?
    @State private var selectedExamID: UUID?
    @State private var isLoading = false
    @State private var errorMessage: String?

    private var selectedOffering: CourseOffering? {
        offerings.first { $0.id == selectedOfferingID }
    }

    private var selectedExam: ExamSummary? {
        exams.first { $0.id == selectedExamID }
    }

    var body: some View {
        ZStack {
            AppBackground()
            ScrollView {
                VStack(spacing: 22) {
                    welcomeCard
                    ScreenTitle(
                        eyebrow: "Hızlı İşlem",
                        title: "Sınav kâğıdı okut",
                        subtitle: "Dersi ve etkin sınavı seçerek seri taramaya başlayın."
                    )
                    AppCard {
                        VStack(alignment: .leading, spacing: 22) {
                            selectionLabel(
                                icon: "books.vertical.fill",
                                title: "Ders ve dönem",
                                detail: selectedOffering?.displayName ?? "Ders seçin"
                            )
                            Picker("Ders açılışı", selection: $selectedOfferingID) {
                                Text("Seçin").tag(UUID?.none)
                                ForEach(offerings) { offering in
                                    Text(offering.displayName).tag(Optional(offering.id))
                                }
                            }
                            .labelsHidden()
                            .pickerStyle(.menu)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(12)
                            .background(InonuTheme.elevatedSurface)
                            .clipShape(RoundedRectangle(cornerRadius: 13))
                            .onChange(of: selectedOfferingID) { newValue in
                                guard let newValue else { return }
                                Task { await loadExams(offeringID: newValue) }
                            }

                            Divider().overlay(InonuTheme.border)

                            selectionLabel(
                                icon: "doc.text.fill",
                                title: "Etkin sınav",
                                detail: selectedExam.map { "\($0.title) • \($0.totalScore) puan" }
                                    ?? "Sınav seçin"
                            )
                            Picker("Etkin sınav", selection: $selectedExamID) {
                                Text("Seçin").tag(UUID?.none)
                                ForEach(exams.filter(\.isScannable)) { exam in
                                    Text("\(exam.title) — \(exam.totalScore) puan")
                                        .tag(Optional(exam.id))
                                }
                            }
                            .labelsHidden()
                            .pickerStyle(.menu)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(12)
                            .background(InonuTheme.elevatedSurface)
                            .clipShape(RoundedRectangle(cornerRadius: 13))

                            if !exams.isEmpty && exams.allSatisfy({ !$0.isScannable }) {
                                Label(
                                    "Bu derste taramaya açık sınav bulunmuyor.",
                                    systemImage: "info.circle"
                                )
                                .font(.footnote)
                                .foregroundStyle(InonuTheme.textSecondary)
                            }
                        }
                    }

                    if let errorMessage {
                        AppCard {
                            Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                                .foregroundStyle(InonuTheme.danger)
                        }
                    }

                    Button {
                        guard let offering = selectedOffering, let exam = selectedExam else { return }
                        onStart(
                            ExamSelection(
                                offeringID: offering.id,
                                examID: exam.id,
                                courseTitle: "\(offering.courseCode) — \(offering.courseName)",
                                examTitle: exam.title
                            )
                        )
                    } label: {
                        Label("Kâğıt Okutmaya Başla", systemImage: "viewfinder")
                    }
                    .buttonStyle(PrimaryActionButtonStyle())
                    .disabled(selectedExam == nil || isLoading)
                    .opacity(selectedExam == nil || isLoading ? 0.5 : 1)

                    AppCard {
                        HStack(spacing: 14) {
                            IconBadge(systemName: "chart.bar.xaxis")
                            VStack(alignment: .leading, spacing: 4) {
                                Text("PÇ analizine hazır")
                                    .font(.headline)
                                    .foregroundStyle(InonuTheme.textPrimary)
                                Text("Onaylanan kâğıtlar raporlara otomatik yansır.")
                                    .font(.subheadline)
                                    .foregroundStyle(InonuTheme.textSecondary)
                            }
                        }
                    }
                }
                .padding(20)
            }
        }
        .overlay {
            if isLoading {
                ProgressView()
                    .padding(22)
                    .background(InonuTheme.surface)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
            }
        }
        .navigationTitle("Ana Sayfa")
        .inonuNavigationChrome()
        .preferredColorScheme(.dark)
        .task { await loadOfferings() }
    }

    private var welcomeCard: some View {
        HStack(spacing: 16) {
            IconBadge(systemName: "person.fill", size: 58)
            VStack(alignment: .leading, spacing: 4) {
                Text("Hoş geldin, \(profile.firstName.uppercased())")
                    .font(.title3.bold())
                    .foregroundStyle(Color(red: 0.02, green: 0.16, blue: 0.20))
                Text("İnönü Üniversitesi • Akademisyen")
                    .font(.subheadline)
                    .foregroundStyle(Color(red: 0.03, green: 0.27, blue: 0.33))
            }
            Spacer()
            Button(action: onProfile) {
                Image(systemName: "person.crop.circle")
                    .font(.title2)
                    .foregroundStyle(InonuTheme.deepBlue)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Profili aç")
        }
        .padding(20)
        .background(InonuTheme.accentGradient)
        .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
    }

    private func selectionLabel(icon: String, title: String, detail: String) -> some View {
        HStack(spacing: 12) {
            IconBadge(systemName: icon)
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.headline)
                    .foregroundStyle(InonuTheme.textPrimary)
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(InonuTheme.textSecondary)
                    .lineLimit(2)
            }
        }
    }

    private func loadOfferings() async {
        isLoading = true
        defer { isLoading = false }
        do {
            offerings = try await api.courseOfferings()
            if selectedOfferingID == nil, let first = offerings.first {
                selectedOfferingID = first.id
                await loadExams(offeringID: first.id)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func loadExams(offeringID: UUID) async {
        isLoading = true
        defer { isLoading = false }
        do {
            exams = try await api.exams(courseOfferingID: offeringID)
            selectedExamID = exams.first(where: \.isScannable)?.id
        } catch {
            exams = []
            selectedExamID = nil
            errorMessage = error.localizedDescription
        }
    }
}
