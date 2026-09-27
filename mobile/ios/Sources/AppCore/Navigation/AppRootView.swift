import SwiftUI

public struct AppRootView: View {
    @State private var path: [AppRoute] = []

    public init() {}

    public var body: some View {
        NavigationStack(path: $path) {
            HomeView {
                path.append(.captureUpload)
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
