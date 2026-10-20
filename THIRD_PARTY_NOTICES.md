# Third-party notices

## `digit-crnn-v3` handwritten numeric recognizer

- Source: https://github.com/asosyal04440/bitirme-projesi
- Source commit: `ed1de27b20635ca8971685d0ec4135523b824ec0`
- Original repository owner / attribution: GitHub user `asosyal04440`
- Integrated artifact: `mobile/ios/Sources/AppCore/Resources/digit-crnn-v3.onnx`
- SHA-256: `84db44945e13991f71fa77e891f6fa5a050c1feba7a1327310e3dc0b05011052`

The preprocessing and CTC decoder in `DigitONNXRecognizer.swift` are a Swift
adaptation of the source repository's Rust and Python implementations. The
recognizer fixtures under `mobile/ios/Tests/AppCoreTests/RecognizerFixtures`
also come from that source commit.

The source repository has no `LICENSE` file at the pinned commit. The project
maintainer reports that the repository owner gave verbal permission for use in
this project on 2026-10-20. That project-specific verbal permission is recorded
for provenance, but it does not establish general MIT relicensing, commercial
rights, sublicensing rights, or redistribution terms. Obtain a written grant or
an upstream license before release beyond the agreed academic/project scope.

The source reports that model v3 was trained/evaluated with synthetic İnönü
sheet crops and handwritten digits/strings from EMNIST, MNIST, USPS and CVL.
Its documentation identifies CVL Digit Strings as CC BY-NC 4.0. Because the
model includes CVL-derived training material, treat the bundled weights as
non-commercial unless the relevant rightsholders provide broader permission.
The source repository does not provide enough licensing evidence to clear USPS
reuse; this remains a release gate. Accuracy reports and test fixtures are not
evidence of license clearance.

## ONNX Runtime

Microsoft ONNX Runtime `1.24.2` is consumed through
https://github.com/microsoft/onnxruntime-swift-package-manager and is licensed
under the MIT License. Its package is pinned in `mobile/ios/Package.resolved`.
