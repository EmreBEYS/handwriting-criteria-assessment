import Testing
@testable import AppCore

@Test func routesRemainDistinct() {
    #expect(AppRoute.captureUpload != AppRoute.analysis)
    #expect(AppRoute.analysis != AppRoute.results)
}
