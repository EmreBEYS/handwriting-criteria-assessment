import Foundation

public struct PendingScan: Codable, Equatable, Sendable {
    public let requestID: UUID
    public let examID: UUID
    public let imageData: Data
    public let createdAt: Date

    public init(requestID: UUID, examID: UUID, imageData: Data, createdAt: Date = Date()) {
        self.requestID = requestID
        self.examID = examID
        self.imageData = imageData
        self.createdAt = createdAt
    }
}

public protocol PendingScanStore: Sendable {
    func save(_ scan: PendingScan) async throws
    func load(examID: UUID) async throws -> PendingScan?
    func remove(requestID: UUID) async throws
    func removeAll() async throws
}

public actor FilePendingScanStore: PendingScanStore {
    private let directory: URL
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    public init(directory: URL? = nil) {
        self.directory = directory
            ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("PendingScans", isDirectory: true)
    }

    public func save(_ scan: PendingScan) throws {
        try ensureDirectory()
        let destination = fileURL(for: scan.requestID)
        try encoder.encode(scan).write(to: destination, options: [.atomic, .completeFileProtection])
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        var protectedDestination = destination
        try protectedDestination.setResourceValues(values)
    }

    public func load(examID: UUID) throws -> PendingScan? {
        guard FileManager.default.fileExists(atPath: directory.path) else { return nil }
        return try FileManager.default.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: nil
        )
        .filter { $0.pathExtension == "pending" }
        .compactMap { url -> PendingScan? in
            guard let data = try? Data(contentsOf: url),
                  let scan = try? decoder.decode(PendingScan.self, from: data),
                  scan.examID == examID
            else { return nil }
            return scan
        }
        .sorted { $0.createdAt < $1.createdAt }
        .first
    }

    public func remove(requestID: UUID) throws {
        let url = fileURL(for: requestID)
        if FileManager.default.fileExists(atPath: url.path) {
            try FileManager.default.removeItem(at: url)
        }
    }

    public func removeAll() throws {
        if FileManager.default.fileExists(atPath: directory.path) {
            try FileManager.default.removeItem(at: directory)
        }
    }

    private func ensureDirectory() throws {
        try FileManager.default.createDirectory(
            at: directory,
            withIntermediateDirectories: true,
            attributes: [.protectionKey: FileProtectionType.complete]
        )
    }

    private func fileURL(for requestID: UUID) -> URL {
        directory.appendingPathComponent("\(requestID.uuidString).pending")
    }
}

public actor InMemoryPendingScanStore: PendingScanStore {
    private var scans: [UUID: PendingScan] = [:]

    public init() {}

    public func save(_ scan: PendingScan) {
        scans[scan.requestID] = scan
    }

    public func load(examID: UUID) -> PendingScan? {
        scans.values.filter { $0.examID == examID }.sorted { $0.createdAt < $1.createdAt }.first
    }

    public func remove(requestID: UUID) {
        scans.removeValue(forKey: requestID)
    }

    public func removeAll() {
        scans.removeAll()
    }
}
