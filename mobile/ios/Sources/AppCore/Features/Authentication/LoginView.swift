import SwiftUI

struct LoginView: View {
    @ObservedObject var session: AppSession
    @State private var institutionCode = ""
    @State private var email = ""
    @State private var password = ""
    @State private var showsPassword = false

    private var canSubmit: Bool {
        !institutionCode.trimmingCharacters(in: .whitespaces).isEmpty
            && email.contains("@")
            && !password.isEmpty
            && !session.isWorking
    }

    var body: some View {
        ZStack {
            AppBackground()
            VStack(spacing: 0) {
                ZStack {
                    InonuTheme.accentGradient
                    Circle()
                        .fill(Color.white.opacity(0.09))
                        .frame(width: 220, height: 220)
                        .offset(x: 130, y: -70)
                    Circle()
                        .fill(Color.white.opacity(0.08))
                        .frame(width: 95, height: 95)
                        .offset(x: -145, y: 70)
                    VStack(spacing: 14) {
                        BrandMark(size: 86)
                        Text("İnönü Üniversitesi")
                            .font(.title2.bold())
                            .foregroundStyle(.white)
                        Text("Sınav Kâğıdı Değerlendirme")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.white.opacity(0.82))
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 300)

                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Hoş geldiniz")
                                .font(.title.bold())
                                .foregroundStyle(InonuTheme.textPrimary)
                            Text("Kurumsal hesabınızla devam edin")
                                .foregroundStyle(InonuTheme.textSecondary)
                        }

                        loginField(icon: "building.columns", title: "Kurum kodu") {
                            TextField("Örn. INONU", text: $institutionCode)
                                .textFieldStyle(.plain)
                        }
                        loginField(icon: "envelope", title: "E-posta adresi") {
                            TextField("ad.soyad@inonu.edu.tr", text: $email)
                                .textFieldStyle(.plain)
                        }
                        loginField(icon: "lock", title: "Şifre") {
                            Group {
                                if showsPassword {
                                    TextField("Şifreniz", text: $password)
                                } else {
                                    SecureField("Şifreniz", text: $password)
                                }
                            }
                            .textFieldStyle(.plain)
                            Button {
                                showsPassword.toggle()
                            } label: {
                                Image(systemName: showsPassword ? "eye.slash" : "eye")
                                    .foregroundStyle(InonuTheme.sky)
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel(showsPassword ? "Şifreyi gizle" : "Şifreyi göster")
                        }

                        if let message = session.errorMessage {
                            Label(message, systemImage: "exclamationmark.triangle.fill")
                                .font(.footnote)
                                .foregroundStyle(InonuTheme.danger)
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
                                ProgressView().tint(InonuTheme.deepBlue)
                            } else {
                                Text("Giriş Yap")
                            }
                        }
                        .buttonStyle(PrimaryActionButtonStyle())
                        .disabled(!canSubmit)
                        .opacity(canSubmit ? 1 : 0.5)

                        HStack(spacing: 10) {
                            Image(systemName: "checkmark.shield.fill")
                            Text("Bilgileriniz güvenli bağlantı üzerinden iletilir.")
                        }
                        .font(.caption)
                        .foregroundStyle(InonuTheme.textSecondary)
                    }
                    .padding(24)
                }
                .background(InonuTheme.background)
                .clipShape(RoundedRectangle(cornerRadius: 30, style: .continuous))
                .offset(y: -24)
            }
        }
        .ignoresSafeArea(edges: .top)
        .preferredColorScheme(.dark)
    }

    private func loginField<Content: View>(
        icon: String,
        title: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(InonuTheme.sky)
                .frame(width: 22)
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.caption)
                    .foregroundStyle(InonuTheme.textSecondary)
                HStack { content() }
                    .foregroundStyle(InonuTheme.textPrimary)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(InonuTheme.elevatedSurface)
        .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 13, style: .continuous)
                .stroke(InonuTheme.border, lineWidth: 1)
        }
    }
}
