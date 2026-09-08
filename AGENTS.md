# PKG Viewer Agent Guide

This file is the repository's authoritative working guidance. Read it before changing code or documentation.

## Product

PKG Viewer is a native-looking desktop application for Windows, Linux, and macOS. macOS is the primary development and day-to-day verification platform for now; Windows and Linux remain supported release targets. It combines package inspection, metadata viewing, icon preview, entry extraction, batch processing, and evidence-based PS4 PKG validation.

The project is heavily based on [Nigel1992/ps4-pkg-validator](https://github.com/Nigel1992/ps4-pkg-validator) and [Oxwald/PS4-pkg-viewer](https://github.com/Oxwald/PS4-pkg-viewer). Read [`CREDITS.md`](CREDITS.md) and preserve applicable upstream notices in derived code and distributions.

## Working rules

- Keep parsing, validation, presentation, and extraction as separate layers.
- Treat a readable package and a trustworthy package as different outcomes. Never report “valid” when a check was skipped; use explicit states such as Pass, Fail, Warning, and Not checked.
- Prefer documented PKG/SFO structures and test fixtures over byte-pattern guesses.
- Preserve raw values alongside formatted values so users can inspect and export evidence.
- Keep platform-specific UI code behind a small portability layer.
- Do not add decryption, signing-key handling, or other security-sensitive functionality without an explicit design review.
- Do not claim real-package, cross-platform, or integrity coverage without the corresponding test evidence.

## Verification

Run focused parser tests and static checks for every change. Report GUI smoke tests, real-PKG tests, and platform tests separately. A passing unit test or `git diff --check` is not proof of Unity-style runtime or device behavior; likewise, a parser test is not proof that the GUI works on all three operating systems.

## Documentation routing

- [`docs/PROJECT_CODEX.md`](docs/PROJECT_CODEX.md) is the compact project entrypoint.
- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) defines user-facing scope and validation semantics.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) defines boundaries and data flow.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) sequences implementation and verification.

Keep this file concise and update it when a durable project rule changes.
