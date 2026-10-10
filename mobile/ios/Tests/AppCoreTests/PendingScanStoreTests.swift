import Foundation
import Testing
@testable import AppCore

@Test
func pendingScanRoundTripAndRemoval() async throws {
    let directory = FileManager.default.temporaryDirectory
        .appendingPathComponent(UUID().uuidString, isDirectory: true)
    let store = FilePendingScanStore(directory: directory)
    let scan = PendingScan(
        requestID: UUID(),
        examID: UUID(),
        imageData: Data([0xFF, 0xD8, 0xFF])
    )

    try await store.save(scan)
    #expect(try await store.load(examID: scan.examID) == scan)

    try await store.remove(requestID: scan.requestID)
    #expect(try await store.load(examID: scan.examID) == nil)
    try? FileManager.default.removeItem(at: directory)
}

@Test
func pendingScanStoreKeepsExamQueuesSeparatedAndCanPurgeAll() async throws {
    let store = InMemoryPendingScanStore()
    let first = PendingScan(requestID: UUID(), examID: UUID(), imageData: Data([1]))
    let second = PendingScan(requestID: UUID(), examID: UUID(), imageData: Data([2]))

    await store.save(first)
    await store.save(second)
    #expect(await store.load(examID: first.examID) == first)
    #expect(await store.load(examID: second.examID) == second)

    await store.removeAll()
    #expect(await store.load(examID: first.examID) == nil)
    #expect(await store.load(examID: second.examID) == nil)
}
