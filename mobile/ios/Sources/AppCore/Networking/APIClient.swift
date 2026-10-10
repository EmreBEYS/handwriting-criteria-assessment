import Foundation

public protocol APITransport: Sendable {
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

public struct URLSessionTransport: APITransport {
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }
        return (data, httpResponse)
    }
}

public actor APIClient {
    private let baseURL: URL
    private let transport: any APITransport
    private let tokenStore: any TokenStore
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    public init(
        baseURL: URL,
        transport: any APITransport = URLSessionTransport(),
        tokenStore: any TokenStore = KeychainTokenStore()
    ) {
        self.baseURL = baseURL
        self.transport = transport
        self.tokenStore = tokenStore
    }

    public func login(institutionCode: String, email: String, password: String) async throws -> UserProfile {
        let body = [
            "institution_code": institutionCode,
            "email": email,
            "password": password,
        ]
        let envelope: AuthEnvelope = try await send(
            path: "/api/v1/auth/login",
            method: "POST",
            body: try encoder.encode(body),
            accessToken: nil
        )
        try await tokenStore.save(envelope.data.tokens)
        return envelope.data.user
    }

    public func restoreProfile() async throws -> UserProfile {
        let envelope: DataEnvelope<UserProfile> = try await authorized(
            path: "/api/v1/users/me"
        )
        return envelope.data
    }

    public func logout() async throws {
        guard let tokens = try await tokenStore.load() else { return }
        do {
            let body = try encoder.encode(["refresh_token": tokens.refreshToken])
            let (data, response) = try await rawRequest(
                path: "/api/v1/auth/logout",
                method: "POST",
                body: body,
                contentType: "application/json",
                accessToken: nil
            )
            try validate(data: data, response: response)
        } catch {
            try await tokenStore.clear()
            throw error
        }
        try await tokenStore.clear()
    }

    public func courseOfferings() async throws -> [CourseOffering] {
        let envelope: DataEnvelope<[CourseOffering]> = try await authorized(
            path: "/api/v1/course-offerings"
        )
        return envelope.data
    }

    public func exams(courseOfferingID: UUID) async throws -> [ExamSummary] {
        let envelope: DataEnvelope<[ExamSummary]> = try await authorized(
            path: "/api/v1/course-offerings/\(courseOfferingID)/exams"
        )
        return envelope.data
    }

    public func roster(courseOfferingID: UUID) async throws -> [RosterStudent] {
        let envelope: DataEnvelope<[Enrollment]> = try await authorized(
            path: "/api/v1/course-offerings/\(courseOfferingID)/enrollments"
        )
        return envelope.data.filter(\.isActive).map(\.student)
    }

    public func uploadScan(
        examID: UUID,
        imageData: Data,
        clientRequestID: UUID = UUID()
    ) async throws -> ScanJob {
        let boundary = "Boundary-\(UUID().uuidString)"
        var body = Data()
        body.appendMultipartField(
            name: "client_request_id",
            value: clientRequestID.uuidString,
            boundary: boundary
        )
        body.appendMultipartFile(
            name: "image",
            filename: "exam-paper.jpg",
            mimeType: "image/jpeg",
            content: imageData,
            boundary: boundary
        )
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        let envelope: DataEnvelope<ScanJob> = try await authorized(
            path: "/api/v1/exams/\(examID)/scans",
            method: "POST",
            body: body,
            contentType: "multipart/form-data; boundary=\(boundary)"
        )
        return envelope.data
    }

    public func scan(id: UUID) async throws -> ScanJob {
        let envelope: DataEnvelope<ScanJob> = try await authorized(
            path: "/api/v1/scans/\(id)"
        )
        return envelope.data
    }

    public func confirmPaper(id: UUID, input: ConfirmationInput) async throws -> ConfirmationResult {
        let envelope: DataEnvelope<ConfirmationResult> = try await authorized(
            path: "/api/v1/papers/\(id)/confirm",
            method: "POST",
            body: try encoder.encode(input)
        )
        return envelope.data
    }

    public func examAnalysis(examID: UUID) async throws -> ExamAnalysis {
        let envelope: DataEnvelope<ExamAnalysis> = try await authorized(
            path: "/api/v1/exams/\(examID)/po-analysis"
        )
        return envelope.data
    }

    public func authorized<Value: Decodable & Sendable>(
        path: String,
        method: String = "GET",
        body: Data? = nil,
        contentType: String = "application/json"
    ) async throws -> Value {
        guard let tokens = try await tokenStore.load() else {
            throw APIClientError.noSession
        }
        do {
            return try await send(
                path: path,
                method: method,
                body: body,
                contentType: contentType,
                accessToken: tokens.accessToken
            )
        } catch APIClientError.server(let statusCode, _, _) where statusCode == 401 {
            let refreshed = try await refresh(tokens.refreshToken)
            return try await send(
                path: path,
                method: method,
                body: body,
                contentType: contentType,
                accessToken: refreshed.accessToken
            )
        }
    }

    public func authorizedData(path: String) async throws -> Data {
        guard let tokens = try await tokenStore.load() else {
            throw APIClientError.noSession
        }
        let (data, response) = try await rawRequest(
            path: path,
            method: "GET",
            body: nil,
            contentType: "application/json",
            accessToken: tokens.accessToken
        )
        try validate(data: data, response: response)
        return data
    }

    private func refresh(_ refreshToken: String) async throws -> TokenPair {
        let body = try encoder.encode(["refresh_token": refreshToken])
        let envelope: AuthEnvelope = try await send(
            path: "/api/v1/auth/refresh",
            method: "POST",
            body: body,
            accessToken: nil
        )
        try await tokenStore.save(envelope.data.tokens)
        return envelope.data.tokens
    }

    private func send<Value: Decodable>(
        path: String,
        method: String,
        body: Data? = nil,
        contentType: String = "application/json",
        accessToken: String?
    ) async throws -> Value {
        let (data, response) = try await rawRequest(
            path: path,
            method: method,
            body: body,
            contentType: contentType,
            accessToken: accessToken
        )
        try validate(data: data, response: response)
        do {
            return try decoder.decode(Value.self, from: data)
        } catch {
            throw APIClientError.invalidResponse
        }
    }

    private func rawRequest(
        path: String,
        method: String,
        body: Data?,
        contentType: String,
        accessToken: String?
    ) async throws -> (Data, HTTPURLResponse) {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw APIClientError.invalidResponse
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        request.setValue(UUID().uuidString, forHTTPHeaderField: "X-Request-ID")
        if let accessToken {
            request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        }
        do {
            return try await transport.data(for: request)
        } catch let error as APIClientError {
            throw error
        } catch {
            throw APIClientError.transport(error.localizedDescription)
        }
    }

    private func validate(data: Data, response: HTTPURLResponse) throws {
        guard (200 ..< 300).contains(response.statusCode) else {
            if let envelope = try? decoder.decode(APIErrorEnvelope.self, from: data) {
                throw APIClientError.server(
                    statusCode: response.statusCode,
                    code: envelope.error.code,
                    message: envelope.error.message
                )
            }
            throw APIClientError.server(
                statusCode: response.statusCode,
                code: "HTTP_\(response.statusCode)",
                message: "İstek tamamlanamadı."
            )
        }
    }
}

private extension Data {
    mutating func appendMultipartField(name: String, value: String, boundary: String) {
        append("--\(boundary)\r\n".data(using: .utf8)!)
        append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
        append("\(value)\r\n".data(using: .utf8)!)
    }

    mutating func appendMultipartFile(
        name: String,
        filename: String,
        mimeType: String,
        content: Data,
        boundary: String
    ) {
        append("--\(boundary)\r\n".data(using: .utf8)!)
        append(
            "Content-Disposition: form-data; name=\"\(name)\"; filename=\"\(filename)\"\r\n"
                .data(using: .utf8)!
        )
        append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        append(content)
        append("\r\n".data(using: .utf8)!)
    }
}
