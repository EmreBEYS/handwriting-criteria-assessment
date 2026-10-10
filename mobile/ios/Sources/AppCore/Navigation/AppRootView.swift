import SwiftUI

public struct AppRootView: View {
    @StateObject private var session: AppSession

    public init(session: AppSession = AppSession()) {
        _session = StateObject(wrappedValue: session)
    }

    public var body: some View {
        Group {
            switch session.phase {
            case .restoring:
                ZStack {
                    AppBackground()
                    VStack(spacing: 18) {
                        BrandMark()
                        ProgressView("Oturum kontrol ediliyor…")
                            .tint(InonuTheme.sky)
                            .foregroundStyle(InonuTheme.textSecondary)
                    }
                }
            case .signedOut:
                LoginView(session: session)
            case let .signedIn(profile):
                AuthenticatedRootView(session: session, profile: profile)
            }
        }
        .task {
            if session.phase == .restoring {
                await session.restore()
            }
        }
    }
}

private struct AuthenticatedRootView: View {
    @ObservedObject var session: AppSession
    let profile: UserProfile
    @State private var path: [AppRoute] = []
    @State private var showsProfile = false

    var body: some View {
        NavigationStack(path: $path) {
            HomeView(
                api: session.api,
                profile: profile,
                onProfile: { showsProfile = true }
            ) { selection in
                path.append(.captureUpload(selection))
            }
            .sheet(isPresented: $showsProfile) {
                ProfileView(session: session, profile: profile)
            }
            .navigationDestination(for: AppRoute.self) { route in
                switch route {
                case let .captureUpload(selection):
                    CaptureUploadView(api: session.api, selection: selection) { scanID in
                        path.append(.analysis(scanID: scanID, selection: selection))
                    }
                case let .analysis(scanID, selection):
                    AnalysisView(
                        api: session.api,
                        scanID: scanID,
                        offeringID: selection.offeringID
                    ) { result in
                        path.append(.results(result, selection))
                    }
                case let .results(result, selection):
                    ResultsView(api: session.api, result: result, selection: selection) {
                        path.removeAll()
                    }
                }
            }
        }
        .tint(InonuTheme.sky)
        .preferredColorScheme(.dark)
    }
}
