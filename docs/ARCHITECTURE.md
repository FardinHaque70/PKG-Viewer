# Architecture

```text
File source -> Binary reader -> PKG model -> SFO/entry decoders
                                      |-> Validation engine -> report
                                      |-> UI view model -> desktop UI
                                      |-> Extraction service -> output files
```

## Boundaries

The first implementation should optimize for macOS development and verification, while keeping filesystem, process, packaging, and UI assumptions portable so Windows and Linux support does not require a redesign.

- **Binary reader:** bounded reads, endianness, overflow-safe offsets, cancellation, and useful errors.
- **PKG decoder:** parses the documented header, entry table, name table, digests, and known entry IDs into typed data while retaining raw fields.
- **SFO decoder:** parses the key table and data table according to format and length fields; do not locate values by searching for marker bytes.
- **Validation engine:** pure checks over the model. Checks must be independently addressable, explainable, and testable.
- **Extraction service:** copies only ranges validated as inside the file; reports encrypted or unavailable content explicitly.
- **UI layer:** platform-neutral view models and native controls. No binary parsing in event handlers.

## Error and trust model

Malformed input is untrusted data. Reject impossible ranges before allocation or reading. A decoder may return partial metadata, but the validation report must preserve the failure that prevented full verification. Use structured diagnostics with severity, check ID, evidence, and source offset.

## Test strategy

Maintain synthetic fixtures for every header and entry boundary, malformed/truncated files, SFO string and integer formats, encrypted entries, and valid samples from each supported package type. Add golden JSON reports and GUI smoke tests on all three operating systems before release.
