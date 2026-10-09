import SwiftUI

struct HomeView: View {
    let api: APIClient
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
        Form {
            Section {
                Label("Sınav Kâğıdı Değerlendirme", systemImage: "doc.text.viewfinder")
                    .font(.title2.bold())
            }
            Section("Ders") {
                Picker("Ders açılışı", selection: $selectedOfferingID) {
                    Text("Seçin").tag(UUID?.none)
                    ForEach(offerings) { offering in
                        Text(offering.displayName).tag(Optional(offering.id))
                    }
                }
                .onChange(of: selectedOfferingID) { newValue in
                    guard let newValue else { return }
                    Task { await loadExams(offeringID: newValue) }
                }
            }
            Section("Sınav") {
                Picker("Etkin sınav", selection: $selectedExamID) {
                    Text("Seçin").tag(UUID?.none)
                    ForEach(exams.filter(\.isScannable)) { exam in
                        Text("\(exam.title) — \(exam.totalScore) puan").tag(Optional(exam.id))
                    }
                }
                if !exams.isEmpty && exams.allSatisfy({ !$0.isScannable }) {
                    Text("Bu derste taramaya açık etkin sınav bulunmuyor.")
                        .foregroundStyle(.secondary)
                }
            }
            if let errorMessage {
                Text(errorMessage).foregroundStyle(.red)
            }
            Button("Kâğıt Okutmaya Başla") {
                guard let offering = selectedOffering, let exam = selectedExam else { return }
                onStart(
                    ExamSelection(
                        offeringID: offering.id,
                        examID: exam.id,
                        courseTitle: "\(offering.courseCode) — \(offering.courseName)",
                        examTitle: exam.title
                    )
                )
            }
            .buttonStyle(.borderedProminent)
            .disabled(selectedExam == nil || isLoading)
        }
        .overlay { if isLoading { ProgressView() } }
        .navigationTitle("Sınav Seçimi")
        .task { await loadOfferings() }
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
