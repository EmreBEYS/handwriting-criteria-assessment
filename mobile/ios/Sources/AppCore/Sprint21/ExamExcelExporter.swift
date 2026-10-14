import Foundation

public enum ExamExcelExporter {
    public static func data(for results: [ExamRecognition]) -> Data {
        let questionNumbers = Array(Set(results.flatMap { $0.questions.map(\.number) })).sorted()
        let columnCount = 6 + questionNumbers.count
        let lastColumn = excelColumnName(columnCount)

        var rows: [String] = []
        rows.append(row(1, [textCell("A1", "SINAV SONUÇLARI", style: 2)], height: 30))
        rows.append(row(2, [
            textCell("A2", "Yüksek güven", style: 5),
            textCell("B2", "Kontrol önerilir", style: 6),
            textCell("C2", "Düşük güven", style: 7),
        ], height: 24))
        rows.append(row(3, [
            textCell("A3", "Her satır bir sınav kâğıdıdır. Renkler OCR okuma güvenini gösterir.", style: 3),
        ]))

        let headers = ["Sıra", "Öğrenci Adı", "Ders", "Okunan Genel Not", "Hesaplanan Toplam", "Genel Güven"]
            + questionNumbers.map { number in
                let outcome = results.lazy
                    .compactMap { result in result.questions.first(where: { $0.number == number })?.programOutcome }
                    .first ?? "PÇ?"
                return "S\(number) (\(outcome))"
            }
        rows.append(row(4, headers.enumerated().map {
            textCell("\(excelColumnName($0.offset + 1))4", $0.element, style: 4)
        }, height: 32))

        for (index, result) in results.enumerated() {
            let rowNumber = index + 5
            let overallLevel = lowestConfidenceLevel(in: result)
            var cells = [
                numberCell("A\(rowNumber)", Double(index + 1), style: 0),
                textCell("B\(rowNumber)", result.studentName.value, style: styleIndex(for: result.studentName.level)),
                textCell("C\(rowNumber)", result.courseTitle, style: 0),
                valueCell("D\(rowNumber)", result.totalScore.value, style: styleIndex(for: result.totalScore.level)),
                numberCell("E\(rowNumber)", result.calculatedTotal, style: 1),
                textCell("F\(rowNumber)", overallLevel.title, style: styleIndex(for: overallLevel)),
            ]
            for (offset, number) in questionNumbers.enumerated() {
                let reference = "\(excelColumnName(offset + 7))\(rowNumber)"
                if let question = result.questions.first(where: { $0.number == number }) {
                    cells.append(valueCell(reference, question.score.value, style: styleIndex(for: question.score.level)))
                } else {
                    cells.append(textCell(reference, "", style: 0))
                }
            }
            rows.append(row(rowNumber, cells, height: 24))
        }

        let questionColumns = questionNumbers.indices.map {
            let index = $0 + 7
            return "<col min=\"\(index)\" max=\"\(index)\" width=\"13\" customWidth=\"1\"/>"
        }.joined()
        let sheet = """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
          <sheetViews><sheetView workbookViewId="0"><pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
          <cols>
            <col min="1" max="1" width="7" customWidth="1"/>
            <col min="2" max="2" width="26" customWidth="1"/>
            <col min="3" max="3" width="20" customWidth="1"/>
            <col min="4" max="6" width="18" customWidth="1"/>
            \(questionColumns)
          </cols>
          <sheetData>\(rows.joined())</sheetData>
          <mergeCells count="2"><mergeCell ref="A1:\(lastColumn)1"/><mergeCell ref="A3:\(lastColumn)3"/></mergeCells>
          <autoFilter ref="A4:\(lastColumn)\(max(results.count + 4, 4))"/>
        </worksheet>
        """

        return ZipArchive.make(entries: [
            ("[Content_Types].xml", contentTypes),
            ("_rels/.rels", rootRelationships),
            ("docProps/app.xml", appProperties),
            ("docProps/core.xml", coreProperties),
            ("xl/workbook.xml", workbook),
            ("xl/_rels/workbook.xml.rels", workbookRelationships),
            ("xl/styles.xml", styles),
            ("xl/worksheets/sheet1.xml", sheet),
        ])
    }

    private static let contentTypes = """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
      <Default Extension="xml" ContentType="application/xml"/>
      <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
      <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
      <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
      <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
      <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
    </Types>
    """

    private static let rootRelationships = """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
      <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
    </Relationships>
    """

    private static let workbook = """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheets><sheet name="Sınav Sonuçları" sheetId="1" r:id="rId1"/></sheets>
    </workbook>
    """

    private static let workbookRelationships = """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
    </Relationships>
    """

    private static let appProperties = """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Handwriting Criteria Assessment</Application></Properties>
    """

    private static let coreProperties = """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sınav Sonuçları</dc:title><dc:creator>Handwriting Criteria Assessment</dc:creator></cp:coreProperties>
    """

    private static let styles = """
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
      <fonts count="4">
        <font><sz val="11"/><color rgb="FF172033"/><name val="Aptos"/></font>
        <font><b/><sz val="16"/><color rgb="FFFFFFFF"/><name val="Aptos Display"/></font>
        <font><i/><sz val="10"/><color rgb="FF44546A"/><name val="Aptos"/></font>
        <font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Aptos"/></font>
      </fonts>
      <fills count="7">
        <fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FF17365D"/><bgColor indexed="64"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FF4472C4"/><bgColor indexed="64"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FFC6EFCE"/><bgColor indexed="64"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FFFFEB9C"/><bgColor indexed="64"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FFFFC7CE"/><bgColor indexed="64"/></patternFill></fill>
      </fills>
      <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
      <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
      <cellXfs count="8">
        <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
        <xf numFmtId="2" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
        <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
        <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
        <xf numFmtId="0" fontId="3" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
        <xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyFill="1"/>
        <xf numFmtId="0" fontId="0" fillId="5" borderId="0" xfId="0" applyFill="1"/>
        <xf numFmtId="0" fontId="0" fillId="6" borderId="0" xfId="0" applyFill="1"/>
      </cellXfs>
      <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
    </styleSheet>
    """

    private static func lowestConfidenceLevel(in result: ExamRecognition) -> ConfidenceLevel {
        let levels = [result.studentName.level, result.totalScore.level] + result.questions.map { $0.score.level }
        if levels.contains(.low) { return .low }
        if levels.contains(.medium) { return .medium }
        return .high
    }

    private static func styleIndex(for level: ConfidenceLevel) -> Int {
        switch level {
        case .high: 5
        case .medium: 6
        case .low: 7
        }
    }

    private static func row(_ number: Int, _ cells: [String], height: Int? = nil) -> String {
        let heightAttributes = height.map { " ht=\"\($0)\" customHeight=\"1\"" } ?? ""
        return "<row r=\"\(number)\"\(heightAttributes)>\(cells.joined())</row>"
    }

    private static func textCell(_ reference: String, _ value: String, style: Int) -> String {
        "<c r=\"\(reference)\" s=\"\(style)\" t=\"inlineStr\"><is><t xml:space=\"preserve\">\(escape(value))</t></is></c>"
    }

    private static func numberCell(_ reference: String, _ value: Double, style: Int) -> String {
        "<c r=\"\(reference)\" s=\"\(style)\" t=\"n\"><v>\(value)</v></c>"
    }

    private static func valueCell(_ reference: String, _ value: String, style: Int) -> String {
        let normalized = value.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: ",", with: ".")
        if let number = Double(normalized) {
            return numberCell(reference, number, style: style)
        }
        return textCell(reference, value, style: style)
    }

    private static func excelColumnName(_ oneBasedIndex: Int) -> String {
        var index = oneBasedIndex
        var name = ""
        while index > 0 {
            index -= 1
            name = String(UnicodeScalar(65 + (index % 26))!) + name
            index /= 26
        }
        return name
    }

    private static func escape(_ value: String) -> String {
        value.replacingOccurrences(of: "&", with: "&amp;")
            .replacingOccurrences(of: "<", with: "&lt;")
            .replacingOccurrences(of: ">", with: "&gt;")
            .replacingOccurrences(of: "\"", with: "&quot;")
            .replacingOccurrences(of: "'", with: "&apos;")
    }
}

private enum ZipArchive {
    private struct CentralEntry {
        let name: Data
        let crc32: UInt32
        let size: UInt32
        let offset: UInt32
    }

    static func make(entries: [(String, String)]) -> Data {
        var archive = Data()
        var centralEntries: [CentralEntry] = []
        for (path, contents) in entries {
            let name = Data(path.utf8)
            let payload = Data(contents.utf8)
            let crc = crc32(payload)
            let offset = UInt32(archive.count)
            archive.appendLittleEndian(UInt32(0x04034B50))
            archive.appendLittleEndian(UInt16(20))
            archive.appendLittleEndian(UInt16(0x0800))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(crc)
            archive.appendLittleEndian(UInt32(payload.count))
            archive.appendLittleEndian(UInt32(payload.count))
            archive.appendLittleEndian(UInt16(name.count))
            archive.appendLittleEndian(UInt16(0))
            archive.append(name)
            archive.append(payload)
            centralEntries.append(CentralEntry(name: name, crc32: crc, size: UInt32(payload.count), offset: offset))
        }

        let centralOffset = UInt32(archive.count)
        for entry in centralEntries {
            archive.appendLittleEndian(UInt32(0x02014B50))
            archive.appendLittleEndian(UInt16(20))
            archive.appendLittleEndian(UInt16(20))
            archive.appendLittleEndian(UInt16(0x0800))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(entry.crc32)
            archive.appendLittleEndian(entry.size)
            archive.appendLittleEndian(entry.size)
            archive.appendLittleEndian(UInt16(entry.name.count))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(UInt16(0))
            archive.appendLittleEndian(UInt32(0))
            archive.appendLittleEndian(entry.offset)
            archive.append(entry.name)
        }

        let centralSize = UInt32(archive.count) - centralOffset
        archive.appendLittleEndian(UInt32(0x06054B50))
        archive.appendLittleEndian(UInt16(0))
        archive.appendLittleEndian(UInt16(0))
        archive.appendLittleEndian(UInt16(centralEntries.count))
        archive.appendLittleEndian(UInt16(centralEntries.count))
        archive.appendLittleEndian(centralSize)
        archive.appendLittleEndian(centralOffset)
        archive.appendLittleEndian(UInt16(0))
        return archive
    }

    private static func crc32(_ data: Data) -> UInt32 {
        var crc = UInt32.max
        for byte in data {
            crc ^= UInt32(byte)
            for _ in 0 ..< 8 {
                crc = (crc >> 1) ^ (crc & 1 == 1 ? 0xEDB88320 : 0)
            }
        }
        return crc ^ UInt32.max
    }
}

private extension Data {
    mutating func appendLittleEndian<T: FixedWidthInteger>(_ value: T) {
        var littleEndian = value.littleEndian
        Swift.withUnsafeBytes(of: &littleEndian) { append(contentsOf: $0) }
    }
}
