import SwiftUI

struct LoginView: View {
    @ObservedObject var session: AppSession
    @State private var institutionCode = ""
    @State private var email = ""
    @State private var password = ""

    private var canSubmit: Bool {
        !institutionCode.trimmingCharacters(in: .whitespaces).isEmpty
            && email.contains("@")
            && !password.isEmpty
            && !session.isWorking
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Kurum Hesabı") {
                    TextField("Kurum kodu", text: $institutionCode)
                    TextField("E-posta", text: $email)
                    SecureField("Parola", text: $password)
                }
                if let message = session.errorMessage {
                    Text(message)
                        .foregroundStyle(.red)
                        .accessibilityLabel("Giriş hatası: \(message)")
                }
                Button {
                    Task {
                        await session.login(
                            institutionCode: institutionCode,
                            email: email,
                            password: password
                        )
                    }
                } label: {
                    if session.isWorking {
                        ProgressView().frame(maxWidth: .infinity)
                    } else {
                        Text("Giriş Yap").frame(maxWidth: .infinity)
                    }
                }
                .disabled(!canSubmit)
            }
            .navigationTitle("Sınav Değerlendirme")
        }
    }
}
