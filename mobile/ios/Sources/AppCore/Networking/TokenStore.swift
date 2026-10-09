import Foundation
import Security

public protocol TokenStore: Sendable {
    func load() async throws -> TokenPair?
    func save(_ tokens: TokenPair) async throws
    func clear() async throws
}

public actor InMemoryTokenStore: TokenStore {
    private var tokens: TokenPair?

    public init(tokens: TokenPair? = nil) {
        self.tokens = tokens
    }

    public func load() -> TokenPair? { tokens }
    public func save(_ tokens: TokenPair) { self.tokens = tokens }
    public func clear() { tokens = nil }
}

public final class KeychainTokenStore: TokenStore, @unchecked Sendable {
    private let service: String
    private let account = "authenticated-token-pair"

    public init(service: String = "com.handwriting-criteria-assessment.session") {
        self.service = service
    }

    public func load() async throws -> TokenPair? {
        var result: CFTypeRef?
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else {
            throw APIClientError.transport("Güvenli oturum bilgisi okunamadı.")
        }
        return try JSONDecoder().decode(TokenPair.self, from: data)
    }

    public func save(_ tokens: TokenPair) async throws {
        let data = try JSONEncoder().encode(tokens)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        let attributes = [kSecValueData as String: data]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var insertion = query
            insertion[kSecValueData as String] = data
            guard SecItemAdd(insertion as CFDictionary, nil) == errSecSuccess else {
                throw APIClientError.transport("Güvenli oturum bilgisi kaydedilemedi.")
            }
        } else if status != errSecSuccess {
            throw APIClientError.transport("Güvenli oturum bilgisi güncellenemedi.")
        }
    }

    public func clear() async throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw APIClientError.transport("Güvenli oturum bilgisi silinemedi.")
        }
    }
}
