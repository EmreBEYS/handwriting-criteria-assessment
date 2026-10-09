import SwiftUI

@MainActor
private final class ReviewViewModel: ObservableObject {
    @Published var scan: ScanJob?
    @Published var students: [RosterStudent] = []
    @Published var selectedStudentID: UUID?
    @Published var scoreTexts: [UUID: String] = [:]
    @Published var correctionReason = ""
    @Published var errorMessage: String?
    @Published var isWorking = false

    let api: APIClient
    let scanID: UUID
    let offeringID: UUID

    init(api: APIClient, scanID: UUID, offeringID: UUID) {
        self.api = api
        self.scanID = scanID
        self.offeringID = offeringID
    }

    func loadUntilReviewable() async {
        isWorking = true
        defer { isWorking = false }
        do {
            students = try await api.roster(courseOfferingID: offeringID)
            for _ in 0 ..< 60 {
                let latest = try await api.scan(id: scanID)
                scan = latest
                if latest.status == "needs_review" || latest.status == "saved" {
                    prepare(latest)
                    return
                }
                if latest.status == "failed" || latest.status == "cancelled" {
                    throw APIClientError.server(
                        statusCode: 409,
                        code: latest.errorCode ?? "SCAN_FAILED",
                        message: latest.errorMessage ?? "Görüntü işlenemedi."
                    )
                }
                try await Task.sleep(for: .seconds(2))
            }
            throw APIClientError.transport(
                "Analiz beklenenden uzun sürdü. Daha sonra yeniden deneyin."
            )
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func confirm() async throws -> ConfirmationResult {
        guard let paper = scan?.paper, let studentID = selectedStudentID else {
            throw APIClientError.transport("Öğrenci ve tüm soru puanları seçilmelidir.")
        }
        let answers = try paper.answers.map { answer in
            let value = scoreTexts[answer.questionID, default: ""]
                .replacingOccurrences(of: ",", with: ".")
            guard let score = Decimal(string: value),
                  let maximum = Decimal(string: answer.maximumScore),
                  score >= 0,
                  score <= maximum
            else {
                throw APIClientError.transport(
                    "Soru \(answer.questionNumber) puanı 0–\(answer.maximumScore) aralığında olmalıdır."
                )
            }
            return FinalAnswerInput(questionID: answer.questionID, finalScore: value)
        }
        return try await api.confirmPaper(
            id: paper.id,
            input: ConfirmationInput(
                studentID: studentID,
                answers: answers,
                correctionReason: correctionReason.isEmpty ? nil : correctionReason
            )
        )
    }

    private func prepare(_ scan: ScanJob) {
        guard let paper = scan.paper else { return }
        selectedStudentID = paper.matchedStudentID ?? students.first?.id
        for answer in paper.answers where scoreTexts[answer.questionID] == nil {
            scoreTexts[answer.questionID] = answer.predictedScore ?? ""
        }
    }
}

struct AnalysisView: View {
    @StateObject private var model: ReviewViewModel
    let onSaved: (ConfirmationResult) -> Void

    init(
        api: APIClient,
        scanID: UUID,
        offeringID: UUID,
        onSaved: @escaping (ConfirmationResult) -> Void
    ) {
        _model = StateObject(
            wrappedValue: ReviewViewModel(api: api, scanID: scanID, offeringID: offeringID)
        )
        self.onSaved = onSaved
    }

    var body: some View {
        ZStack {
            AppBackground()
            ScrollView {
                VStack(spacing: 22) {
                    ScreenTitle(
                        eyebrow: "Model Sonucu",
                        title: "Tahmini incele",
                        subtitle: "Öğrenci ve soru puanlarını kontrol ettikten sonra kesinleştirin."
                    )
                    if model.scan?.isPending != false {
                        AppCard {
                            HStack(spacing: 16) {
                                ProgressView().tint(InonuTheme.sky)
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Kâğıt analiz ediliyor")
                                        .font(.headline)
                                    Text("Bu ekran sonuç hazır olduğunda otomatik güncellenecek.")
                                        .font(.caption)
                                        .foregroundStyle(InonuTheme.textSecondary)
                                }
                            }
                        }
                    }
                    if let paper = model.scan?.paper {
                        AppCard {
                            VStack(alignment: .leading, spacing: 18) {
                                HStack {
                                    IconBadge(systemName: "person.text.rectangle.fill")
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text("Öğrenci Eşleştirme")
                                            .font(.headline)
                                        if let number = paper.predictedStudentNumber {
                                            Text("Model tahmini: \(number)")
                                                .font(.caption)
                                                .foregroundStyle(InonuTheme.textSecondary)
                                        }
                                    }
                                }
                                Picker("Kesin öğrenci", selection: $model.selectedStudentID) {
                                    Text("Öğrenci seçin").tag(UUID?.none)
                                    ForEach(model.students) { student in
                                        Text(student.displayName).tag(Optional(student.id))
                                    }
                                }
                                .pickerStyle(.menu)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(12)
                                .background(InonuTheme.elevatedSurface)
                                .clipShape(RoundedRectangle(cornerRadius: 13))
                            }
                        }

                        AppCard {
                            VStack(alignment: .leading, spacing: 15) {
                                HStack {
                                    IconBadge(systemName: "list.number")
                                    Text("Soru Puanları")
                                        .font(.headline)
                                }
                                ForEach(paper.answers) { answer in
                                    HStack(spacing: 12) {
                                        VStack(alignment: .leading, spacing: 3) {
                                            Text("Soru \(answer.questionNumber)")
                                                .font(.body.weight(.semibold))
                                            if answer.requiresReview {
                                                StatusPill(
                                                    title: "Kontrol gerekli",
                                                    systemName: "exclamationmark.triangle.fill",
                                                    color: .orange
                                                )
                                            }
                                        }
                                        Spacer()
                                        TextField(
                                            "0",
                                            text: Binding(
                                                get: {
                                                    model.scoreTexts[answer.questionID, default: ""]
                                                },
                                                set: { model.scoreTexts[answer.questionID] = $0 }
                                            )
                                        )
                                        .textFieldStyle(.plain)
                                        .multilineTextAlignment(.trailing)
                                        .padding(11)
                                        .frame(width: 78)
                                        .background(InonuTheme.elevatedSurface)
                                        .clipShape(RoundedRectangle(cornerRadius: 11))
                                        Text("/ \(answer.maximumScore)")
                                            .font(.subheadline.monospacedDigit())
                                            .foregroundStyle(InonuTheme.textSecondary)
                                    }
                                    if answer.id != paper.answers.last?.id {
                                        Divider().overlay(InonuTheme.border)
                                    }
                                }
                            }
                        }

                        if !paper.reviewReasons.isEmpty {
                            AppCard {
                                VStack(alignment: .leading, spacing: 12) {
                                    Text("İNCELEME UYARILARI")
                                        .font(.caption.bold())
                                        .tracking(1.2)
                                        .foregroundStyle(.orange)
                                    ForEach(paper.reviewReasons, id: \.self) { reason in
                                        Label(reason, systemImage: "exclamationmark.triangle")
                                            .font(.subheadline)
                                    }
                                }
                            }
                        }

                        AppCard {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("Düzeltme notu")
                                    .font(.headline)
                                TextField("İsteğe bağlı açıklama", text: $model.correctionReason)
                                    .textFieldStyle(.plain)
                                    .padding(12)
                                    .background(InonuTheme.elevatedSurface)
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                            }
                        }

                        Button {
                            Task {
                                do {
                                    onSaved(try await model.confirm())
                                } catch {
                                    model.errorMessage = error.localizedDescription
                                }
                            }
                        } label: {
                            Label("Onayla ve Kaydet", systemImage: "checkmark.seal.fill")
                        }
                        .buttonStyle(PrimaryActionButtonStyle())
                        .disabled(model.selectedStudentID == nil || model.isWorking)
                        .opacity(model.selectedStudentID == nil || model.isWorking ? 0.5 : 1)
                    }
                    if let errorMessage = model.errorMessage {
                        AppCard {
                            Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                                .foregroundStyle(InonuTheme.danger)
                        }
                    }
                }
                .padding(20)
            }
        }
        .navigationTitle("Tahmini İncele")
        .inonuNavigationChrome()
        .preferredColorScheme(.dark)
        .task { await model.loadUntilReviewable() }
    }
}
