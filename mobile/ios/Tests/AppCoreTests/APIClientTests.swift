import Foundation
import Testing
@testable import AppCore

private actor StubTransport: APITransport {
    private var responses: [(Int, Data)]
    private(set) var requests: [URLRequest] = []

    init(responses: [(Int, Data)]) {
        self.responses = responses
    }

    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        requests.append(request)
        let response = responses.removeFirst()
        return (
            response.1,
            HTTPURLResponse(
                url: request.url!,
                statusCode: response.0,
                httpVersion: nil,
                headerFields: nil
            )!
        )
    }
}

private let userID = "00000000-0000-0000-0000-000000000001"
private let institutionID = "00000000-0000-0000-0000-000000000002"

private func authJSON(access: String = "access", refresh: String = "refresh") -> Data {
    Data(
        """
        {"data":{"user":{"id":"\(userID)","institution_id":"\(institutionID)",
        "email":"ada@example.edu","first_name":"Ada","last_name":"Lovelace",
        "role":"instructor"},"tokens":{"access_token":"\(access)",
        "refresh_token":"\(refresh)","token_type":"bearer","expires_in":900}}}
        """.utf8
    )
}

@Test
func loginPersistsTokensAndUsesNormalizedEndpoint() async throws {
    let transport = StubTransport(responses: [(200, authJSON())])
    let store = InMemoryTokenStore()
    let client = APIClient(
        baseURL: URL(string: "https://api.example.test")!,
        transport: transport,
        tokenStore: store
    )

    let profile = try await client.login(
        institutionCode: "EXAMPLE",
        email: "ada@example.edu",
        password: "a-strong-password"
    )

    #expect(profile.displayName == "Ada Lovelace")
    let savedTokens = await store.load()
    #expect(savedTokens?.accessToken == "access")
    let request = await transport.requests.first
    #expect(request?.url?.path == "/api/v1/auth/login")
    #expect(request?.httpMethod == "POST")
}

@Test
func authorizedRequestRefreshesOnceAfterUnauthorized() async throws {
    let unauthorized = Data(
        """
        {"error":{"code":"INVALID_TOKEN","message":"Expired","request_id":"request"}}
        """.utf8
    )
    let profile = Data(
        """
        {"data":{"id":"\(userID)","institution_id":"\(institutionID)",
        "email":"ada@example.edu","first_name":"Ada","last_name":"Lovelace",
        "role":"instructor"}}
        """.utf8
    )
    let transport = StubTransport(
        responses: [(401, unauthorized), (200, authJSON(access: "new-access")), (200, profile)]
    )
    let store = InMemoryTokenStore(
        tokens: TokenPair(accessToken: "old-access", refreshToken: "refresh", expiresIn: 900)
    )
    let client = APIClient(
        baseURL: URL(string: "https://api.example.test")!,
        transport: transport,
        tokenStore: store
    )

    let restored = try await client.restoreProfile()

    #expect(restored.email == "ada@example.edu")
    let refreshedTokens = await store.load()
    #expect(refreshedTokens?.accessToken == "new-access")
    let requests = await transport.requests
    #expect(requests.count == 3)
    #expect(requests[2].value(forHTTPHeaderField: "Authorization") == "Bearer new-access")
}
