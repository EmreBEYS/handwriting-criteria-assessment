import SwiftUI

enum InonuTheme {
    static let background = Color(red: 0.035, green: 0.055, blue: 0.065)
    static let surface = Color(red: 0.085, green: 0.115, blue: 0.125)
    static let elevatedSurface = Color(red: 0.12, green: 0.16, blue: 0.17)
    static let border = Color.white.opacity(0.16)
    static let textPrimary = Color(red: 0.93, green: 0.96, blue: 0.98)
    static let textSecondary = Color(red: 0.67, green: 0.73, blue: 0.76)
    static let sky = Color(red: 0.49, green: 0.82, blue: 0.98)
    static let turquoise = Color(red: 0.12, green: 0.73, blue: 0.69)
    static let deepBlue = Color(red: 0.02, green: 0.26, blue: 0.35)
    static let danger = Color(red: 0.95, green: 0.35, blue: 0.38)

    static let accentGradient = LinearGradient(
        colors: [sky, turquoise],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
}

struct AppBackground: View {
    var body: some View {
        ZStack {
            InonuTheme.background
            Circle()
                .fill(InonuTheme.deepBlue.opacity(0.32))
                .frame(width: 330, height: 330)
                .blur(radius: 12)
                .offset(x: 170, y: -360)
            Circle()
                .fill(InonuTheme.turquoise.opacity(0.12))
                .frame(width: 260, height: 260)
                .blur(radius: 24)
                .offset(x: -180, y: 390)
        }
        .ignoresSafeArea()
    }
}

struct BrandMark: View {
    var size: CGFloat = 82

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.white.opacity(0.9), lineWidth: 1.5)
            Text("İÜ")
                .font(.system(size: size * 0.4, weight: .bold, design: .rounded))
                .foregroundStyle(.white)
        }
        .frame(width: size, height: size)
        .accessibilityLabel("İnönü Üniversitesi")
    }
}

struct ScreenTitle: View {
    let eyebrow: String
    let title: String
    var subtitle: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(eyebrow.uppercased())
                .font(.caption.weight(.bold))
                .tracking(1.4)
                .foregroundStyle(InonuTheme.sky)
            Text(title)
                .font(.largeTitle.bold())
                .foregroundStyle(InonuTheme.textPrimary)
            if let subtitle {
                Text(subtitle)
                    .font(.subheadline)
                    .foregroundStyle(InonuTheme.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct AppCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(InonuTheme.surface.opacity(0.96))
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(InonuTheme.border, lineWidth: 1)
            }
    }
}

struct IconBadge: View {
    let systemName: String
    var size: CGFloat = 44

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: size * 0.38, weight: .semibold))
            .foregroundStyle(InonuTheme.sky)
            .frame(width: size, height: size)
            .background(InonuTheme.deepBlue.opacity(0.72))
            .clipShape(Circle())
    }
}

struct StatusPill: View {
    let title: String
    let systemName: String
    var color: Color = InonuTheme.sky

    var body: some View {
        Label(title, systemImage: systemName)
            .font(.caption.weight(.semibold))
            .foregroundStyle(color)
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .background(color.opacity(0.14))
            .clipShape(Capsule())
    }
}

struct PrimaryActionButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundStyle(Color(red: 0.02, green: 0.12, blue: 0.16))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 15)
            .background {
                InonuTheme.accentGradient
                    .opacity(configuration.isPressed ? 0.72 : 1)
            }
            .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
            .scaleEffect(configuration.isPressed ? 0.985 : 1)
    }
}

struct SecondaryActionButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundStyle(InonuTheme.sky)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(InonuTheme.elevatedSurface.opacity(configuration.isPressed ? 0.7 : 1))
            .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 15, style: .continuous)
                    .stroke(InonuTheme.border, lineWidth: 1)
            }
    }
}

extension View {
    func inonuScreen() -> some View {
        scrollContentBackground(.hidden)
            .background(AppBackground())
            .tint(InonuTheme.sky)
            .foregroundStyle(InonuTheme.textPrimary)
    }

    @ViewBuilder
    func inonuNavigationChrome() -> some View {
#if os(iOS)
        toolbarBackground(InonuTheme.background, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
#else
        self
#endif
    }
}
