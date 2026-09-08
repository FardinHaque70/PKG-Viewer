# Product specification

## Provenance

The initial product concept and implementation direction intentionally build heavily on [PS4 PKG Validator](https://github.com/Nigel1992/ps4-pkg-validator) and [PS4-pkg-viewer](https://github.com/Oxwald/PS4-pkg-viewer). Their authors and repositories must remain credited in project documentation and shipped attribution materials. See [`CREDITS.md`](../CREDITS.md).

## Goal

Give a user one clear answer to three questions: What is this package? What can be safely read or extracted? Can its structure and integrity be trusted?

## Initial feature set

- Open one or many `.pkg` files through a file picker or drag and drop.
- Show title, icon, Content ID, Title ID, category, package type, versions, firmware requirement, size, flags, counts, offsets, and hashes where available.
- Display package entries, encryption flags, byte ranges, names, and extraction availability.
- Extract selected metadata or entries to a user-selected folder; never overwrite silently.
- Validate each package with a check list and export a human-readable report plus machine-readable JSON.
- Copy individual values and filter or sort a batch result list.

## Validation language

Each check has a result: **Pass**, **Fail**, **Warning**, or **Not checked**, with evidence and an actionable explanation. Structural checks include magic, header bounds, table bounds, entry bounds, non-overlap rules where applicable, and required metadata presence. Integrity checks are reported separately from structural checks. Encryption or unavailable keys must produce “Not checked,” never an inferred pass.

## UI

Use a restrained native desktop layout: toolbar, package list, overview card, tabbed details, and a status/progress bar. Support light and dark system themes, keyboard navigation, accessible labels, and responsive behavior at modest window sizes. Keep raw values available under Advanced without overwhelming the Overview.

## Out of scope for the first release

PKG building, editing, bypassing protections, online title databases, automatic firmware claims beyond package-declared evidence, and decryption that requires undistributed keys.
