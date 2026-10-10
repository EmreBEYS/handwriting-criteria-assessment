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

@Test
func logoutRevokesServerSessionAndClearsLocalTokens() async throws {
    let transport = StubTransport(responses: [(204, Data())])
    let store = InMemoryTokenStore(
        tokens: TokenPair(accessToken: "access", refreshToken: "refresh", expiresIn: 900)
    )
    let client = APIClient(
        baseURL: URL(string: "https://api.example.test")!,
        transport: transport,
        tokenStore: store
    )

    try await client.logout()

    #expect(await store.load() == nil)
    let request = await transport.requests.first
    #expect(request?.url?.path == "/api/v1/auth/logout")
    let requestBody = String(decoding: request?.httpBody ?? Data(), as: UTF8.self)
    #expect(requestBody.contains("refresh"))
}

@Test
func uploadBuildsIdempotentMultipartRequest() async throws {
    let scanID = UUID()
    let examID = UUID()
    let response = Data(
        """
        {"data":{"id":"\(scanID)","exam_id":"\(examID)","status":"queued",
        "model_version":null,"error_code":null,"error_message":null,"saved_at":null,
        "paper":null}}
        """.utf8
    )
    let transport = StubTransport(responses: [(202, response)])
    let store = InMemoryTokenStore(
        tokens: TokenPair(accessToken: "access", refreshToken: "refresh", expiresIn: 900)
    )
    let client = APIClient(
        baseURL: URL(string: "https://api.example.test")!,
        transport: transport,
        tokenStore: store
    )
    let requestID = UUID()

    let scan = try await client.uploadScan(
        examID: examID,
        imageData: Data([0xFF, 0xD8, 0xFF]),
        clientRequestID: requestID
    )

    #expect(scan.id == scanID)
    let request = await transport.requests.first
    #expect(request?.url?.path == "/api/v1/exams/\(examID)/scans")
    #expect(request?.value(forHTTPHeaderField: "Authorization") == "Bearer access")
    #expect(request?.value(forHTTPHeaderField: "Content-Type")?.hasPrefix("multipart/form-data") == true)
    let body = String(decoding: request?.httpBody ?? Data(), as: UTF8.self)
    #expect(body.contains(requestID.uuidString))
    #expect(body.contains("filename=\"exam-paper.jpg\""))
}

@Test
func loadsProgramOutcomeAnalysisForSelectedExam() async throws {
    let examID = UUID()
    let outcomeID = UUID()
    let response = Data(
        """
        {"data":{"exam_id":"\(examID)","confirmed_paper_count":2,"questions":[],
        "program_outcomes":[{"program_outcome_id":"\(outcomeID)","code":"PÇ1",
        "description":"Problem çözme","achieved_score":"15.000",
        "maximum_score":"20.000","success_percentage":"75.00"}]}}
        """.utf8
    )
    let transport = StubTransport(responses: [(200, response)])
    let store = InMemoryTokenStore(
        tokens: TokenPair(accessToken: "access", refreshToken: "refresh", expiresIn: 900)
    )
    let client = APIClient(
        baseURL: URL(string: "https://api.example.test")!,
        transport: transport,
        tokenStore: store
    )

    let analysis = try await client.examAnalysis(examID: examID)

    #expect(analysis.confirmedPaperCount == 2)
    #expect(analysis.programOutcomes.first?.successPercentage == "75.00")
    let request = await transport.requests.first
    #expect(request?.url?.path == "/api/v1/exams/\(examID)/po-analysis")
}
