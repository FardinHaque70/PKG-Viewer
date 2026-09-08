# Roadmap

## Platform strategy

Develop and verify each phase on macOS first. Add Windows and Linux smoke coverage as features stabilize, then require clean-install and release checks on all three platforms in Phase 4.

## Phase 1: foundation

Choose the UI/runtime stack, define the typed PKG and SFO models, implement bounded binary reading, and add malformed synthetic fixtures. Proof: parser tests and exported diagnostic examples.

## Phase 2: inspection

Implement Overview, Advanced, Entries, icon preview, copying, batch loading, and report export. Proof: GUI smoke test plus fixture-to-screen checks.

## Phase 3: trustworthy validation

Add independent structural checks, digest verification where the format and available data permit it, explicit encryption/key states, and regression cases for known parser failures. Proof: each check has passing and failing fixtures.

## Phase 4: extraction and release

Add safe selected-entry extraction, cancellation, collision handling, packaging, signing of the application itself, and Windows/Linux/macOS CI. Proof: clean-install tests and real-package verification on each platform.
