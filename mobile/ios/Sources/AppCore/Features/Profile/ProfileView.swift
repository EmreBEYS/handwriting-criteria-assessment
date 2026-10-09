import SwiftUI

struct ProfileView: View {
    @ObservedObject var session: AppSession
    let profile: UserProfile
    @Environment(\.dismiss) private var dismiss

    private var initials: String {
        let first = profile.firstName.first.map(String.init) ?? ""
        let last = profile.lastName.first.map(String.init) ?? ""
        return (first + last).uppercased()
    }

    var body: some View {
        NavigationStack {
            ZStack {
                AppBackground()
                ScrollView {
                    VStack(spacing: 24) {
                        ZStack {
                            Circle().fill(InonuTheme.deepBlue)
                            Text(initials)
                                .font(.system(size: 38, weight: .semibold, design: .rounded))
                                .foregroundStyle(InonuTheme.sky)
                        }
                        .frame(width: 112, height: 112)

                        VStack(spacing: 10) {
                            Text(profile.displayName.uppercased())
                                .font(.title2.bold())
                                .foregroundStyle(InonuTheme.textPrimary)
                            StatusPill(
                                title: profile.role == "instructor" ? "Öğretim Elemanı" : profile.role,
                                systemName: "graduationcap.fill"
                            )
                        }

                        AppCard {
                            VStack(alignment: .leading, spacing: 20) {
                                Text("HESAP BİLGİLERİ")
                                    .font(.headline)
                                    .foregroundStyle(InonuTheme.sky)
                                profileRow(icon: "envelope.fill", label: "Kurumsal E-posta", value: profile.email)
                                Divider().overlay(InonuTheme.border)
                                profileRow(icon: "building.columns.fill", label: "Kurum Kimliği", value: profile.institutionID.uuidString)
                                Divider().overlay(InonuTheme.border)
                                profileRow(icon: "person.badge.key.fill", label: "Yetki", value: "Sınav değerlendirme ve raporlama")
                            }
                        }

                        Button(role: .destructive) {
                            Task {
                                await session.logout()
                                dismiss()
                            }
                        } label: {
                            Label("Güvenli Çıkış Yap", systemImage: "rectangle.portrait.and.arrow.right")
                        }
                        .buttonStyle(SecondaryActionButtonStyle())
                    }
                    .padding(20)
                }
            }
            .navigationTitle("Profilim")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Kapat") { dismiss() }
                }
            }
        }
        .preferredColorScheme(.dark)
    }

    private func profileRow(icon: String, label: String, value: String) -> some View {
        HStack(alignment: .top, spacing: 14) {
            Image(systemName: icon)
                .foregroundStyle(InonuTheme.textSecondary)
                .frame(width: 24)
            VStack(alignment: .leading, spacing: 5) {
                Text(label)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(InonuTheme.textSecondary)
                Text(value)
                    .font(.body)
                    .foregroundStyle(InonuTheme.textPrimary)
                    .textSelection(.enabled)
            }
        }
    }
}
