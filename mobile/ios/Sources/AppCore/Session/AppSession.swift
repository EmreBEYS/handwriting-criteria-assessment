import Foundation
import SwiftUI

@MainActor
public final class AppSession: ObservableObject {
    public enum Phase: Equatable {
        case restoring
        case signedOut
        case signedIn(UserProfile)
    }

    @Published public private(set) var phase: Phase = .restoring
    @Published public private(set) var isWorking = false
    @Published public private(set) var errorMessage: String?

    public let api: APIClient

    public init(api: APIClient) {
        self.api = api
    }

    public convenience init() {
        self.init(
            api: APIClient(baseURL: URL(string: "http://127.0.0.1:8000")!)
        )
    }

    public func restore() async {
        do {
            let profile = try await api.restoreProfile()
            phase = .signedIn(profile)
        } catch APIClientError.noSession {
            phase = .signedOut
        } catch {
            phase = .signedOut
            errorMessage = error.localizedDescription
        }
    }

    public func login(institutionCode: String, email: String, password: String) async {
        isWorking = true
        errorMessage = nil
        defer { isWorking = false }
        do {
            let profile = try await api.login(
                institutionCode: institutionCode,
                email: email,
                password: password
            )
            phase = .signedIn(profile)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    public func logout() async {
        try? await api.logout()
        phase = .signedOut
    }
}
