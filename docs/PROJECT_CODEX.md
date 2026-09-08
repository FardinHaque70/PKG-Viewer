# PKG Viewer project entrypoint

PKG Viewer is a cross-platform desktop tool for inspecting and validating PS4 `.pkg` files on Windows, Linux, and macOS. Development and day-to-day verification currently happen on macOS; Windows and Linux are supported release targets.

## Attribution

This project is heavily based on the work in [Nigel1992/ps4-pkg-validator](https://github.com/Nigel1992/ps4-pkg-validator) and [Oxwald/PS4-pkg-viewer](https://github.com/Oxwald/PS4-pkg-viewer). See the repository-level [credits and attribution record](../CREDITS.md). Preserve applicable upstream copyright and license notices when code is reused or distributed.

## Read next

1. [Product specification](PRODUCT_SPEC.md) for scope, screens, and validation language.
2. [Architecture](ARCHITECTURE.md) for parser, validator, UI, and extraction boundaries.
3. [Roadmap](ROADMAP.md) for staged delivery and proof requirements.

## Reference tools

- [Nigel1992/ps4-pkg-validator](https://github.com/Nigel1992/ps4-pkg-validator): drag-and-drop validation and metadata display.
- [Oxwald/PS4-pkg-viewer](https://github.com/Oxwald/PS4-pkg-viewer): icon preview, metadata viewing, entry extraction, and dump commands.
- [LibOrbisPkg format reference](https://github.com/maxton/LibOrbisPkg): reference for PKG entry structures and supported package concepts.

The references inform features; their parsing shortcuts are not automatically correctness guarantees.
