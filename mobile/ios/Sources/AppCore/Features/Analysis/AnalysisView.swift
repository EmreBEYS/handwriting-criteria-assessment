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
        Form {
            if model.scan?.isPending != false {
                Section {
                    ProgressView("Kâğıt analiz ediliyor…")
                }
            }
            if let paper = model.scan?.paper {
                Section("Öğrenci") {
                    if let number = paper.predictedStudentNumber {
                        LabeledContent("Tahmin", value: number)
                    }
                    Picker("Kesin öğrenci", selection: $model.selectedStudentID) {
                        Text("Seçin").tag(UUID?.none)
                        ForEach(model.students) { student in
                            Text(student.displayName).tag(Optional(student.id))
                        }
                    }
                }
                Section("Soru Puanları") {
                    ForEach(paper.answers) { answer in
                        HStack {
                            Text("Soru \(answer.questionNumber)")
                            Spacer()
                            TextField(
                                "0–\(answer.maximumScore)",
                                text: Binding(
                                    get: { model.scoreTexts[answer.questionID, default: ""] },
                                    set: { model.scoreTexts[answer.questionID] = $0 }
                                )
                            )
                            .frame(width: 100)
                            Text("/ \(answer.maximumScore)").foregroundStyle(.secondary)
                        }
                    }
                }
                if !paper.reviewReasons.isEmpty {
                    Section("İnceleme Uyarıları") {
                        ForEach(paper.reviewReasons, id: \.self) { reason in
                            Label(reason, systemImage: "exclamationmark.triangle")
                        }
                    }
                }
                Section("Düzeltme Notu") {
                    TextField("İsteğe bağlı", text: $model.correctionReason)
                }
                Button("Onayla ve Kaydet") {
                    Task {
                        do {
                            onSaved(try await model.confirm())
                        } catch {
                            model.errorMessage = error.localizedDescription
                        }
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(model.selectedStudentID == nil || model.isWorking)
            }
            if let errorMessage = model.errorMessage {
                Text(errorMessage).foregroundStyle(.red)
            }
        }
        .navigationTitle("Tahmini İncele")
        .task { await model.loadUntilReviewable() }
    }
}
