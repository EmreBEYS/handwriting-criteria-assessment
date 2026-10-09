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
                ProgressView("Oturum kontrol ediliyor…")
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

    var body: some View {
        NavigationStack(path: $path) {
            HomeView {
                path.append(.captureUpload)
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Menu(profile.displayName) {
                        Button("Çıkış Yap", role: .destructive) {
                            Task { await session.logout() }
                        }
                    }
                }
            }
            .navigationDestination(for: AppRoute.self) { route in
                switch route {
                case .captureUpload:
                    CaptureUploadView {
                        path.append(.analysis)
                    }
                case .analysis:
                    AnalysisView {
                        path.append(.results)
                    }
                case .results:
                    ResultsView {
                        path.removeAll()
                    }
                }
            }
        }
    }
}
